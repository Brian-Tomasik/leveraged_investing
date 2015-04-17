MAX_CAPITAL_LOSS_DEDUCTION_PER_YEAR = -3000

class Taxes(object):
    """Investor's tax info"""

    def __init__(self, tax_rates):
        self.__tax_rates = tax_rates
        self.__accumulated_short_term_cap_gains = 0 # like Total on p. 1 of Form 8949 http://www.irs.gov/pub/irs-pdf/f8949.pdf
        self.__accumulated_long_term_cap_gains = 0 # like Total on p. 2 of Form 8949 http://www.irs.gov/pub/irs-pdf/f8949.pdf

    @property
    def tax_rates(self):
        return self.__tax_rates

    def process_taxes(self):
        (bill_or_refund, short_term_carryover_loss, long_term_carryover_loss) = self.__get_tax_bill_or_refund_and_carryover()
        self.__set_tax_liabilities_to_zero() # start afresh for next year's amounts; I'm pretending that the tax year ends on the same day as taxes are paid for simplicity
        self.__accumulated_short_term_cap_gains += short_term_carryover_loss
        self.__accumulated_long_term_cap_gains += long_term_carryover_loss
        return bill_or_refund

    def current_estimate_of_tax_bill_or_refund(self):
        (bill_or_refund, short_term_carryover_loss, long_term_carryover_loss) = self.__get_tax_bill_or_refund_and_carryover()
        return bill_or_refund

    def __get_tax_carryovers(self, short_term_gain, long_term_gain, already_deducted):
        """
        The following logic should match the idea behind the
        "Capital Loss Carryover Worksheet" (p. D-11 of 
        http://www.irs.gov/pub/irs-pdf/i1040sd.pdf ).

        Let D be the amount deducted last year, between $0 and $3000.
        Let this year's short-term cap loss be S (loss is a positive number) and
        long-term cap loss be L (loss is a positive number).
        Here are the lines of the "Capital Loss Carryover Worksheet":
        1. 0 (ignore regular income deductions carried forward)
        2. D
        3. D
        4. D
        5. max(S,0) and if 0, goto 9
        6. if L > 0 then 0 else -L  # if a loss, enter 0, otherwise enter gain
        7. if L > 0 then D else -L + D  # add lines 4 and 6
        8. max(0, if L > 0 then max(S,0) - D else max(S,0) + L - D)

        Let's look at cases for line 8:
        if S > D and L > 0, line 8 is
            max(0, S - D) = S-D  # the short-term carryover is however much S exceeds D
        elif S > D and L <= 0, line 8 is
            max(0, S + L - D)  # first cancel out long-term gain against short-term loss before subtracting D
        elif S <= D and L > 0, line 8 is
            max(0, max(S,0) - D) = 0  # because either 0 <= S <= D, 
            # in which case the expression becomes max(0, S - D), with the 0 being bigger
            # or else S < 0 in which case max(S,0) = 0, in which case it's max(0, -D) = 0
        elif S <= D and L <= 0, lin 8 is
            max(0, max(S,0) + L - D) = 0  # this is because even if S > 0, S-D < 0, and L < 0, so the whole right side of the max(,) expression is negative
            # This makes sense because there was no long-term capital loss, and the short-term capital loss was fully covered by D

        9. max(L,0)
        10. if S > 0 then 0 else -S  # if a loss, enter 0, else enter the gain as a positive number
        11. max(0, D - max(S,0))
        12. if S > 0 then max(0, D - max(S,0)) else max(0, D - max(S,0)) - S
        ==> if S > 0 then max(0, D - S) else max(0, D - 0) - S
        ==> if S > 0 then max(0, D - S) else D - S  # since D is always at least 0
        # if S <= 0 then D-S is always > 0, so if S <= 0, max(0, D-S) = D-S. Hence we can
        # get rid of the cases:
        ==> max(0, D-S)
        13. max(0, max(L,0) - max(0, D-S))

        Let's look at cases for line 13:
        if S > D and L > 0, line 13 is
            max(0, L - 0) = L
        elif S > D and L <= 0, line 13 is
            max(0, 0 - max(0,D-S)) = max(0, 0 - 0) = 0  # because D-S is negative; this makes sense since L is a gain!
        elif S <= D and L > 0, line 13 is
            max(0, L - max(0, D-S)) = max(0, L - (D-S))  # L takes care of the part of D that S didn't get to, then carry over what's left
        elif S <= D and L <= 0, line 13 is
            max(0, 0 - (D-S)) = 0  # if there was any short-term loss, D already covered it, and there was no long-term loss to carry over

        Now, combine the conclusions:
        if S > D and L > 0:
            short_term_carry = S-D
            long_term_carry = L
        elif S > D and L <= 0:
            short_term_carry = max(0, S + L - D)
            long_term_carry = 0
        elif S <= D and L > 0:
            short_term_carry = 0
            long_term_carry = max(0, L - (D-S))
        elif S <= D and L <= 0:
            short_term_carry = 0
            long_term_carry = 0

        Since I'm using negative variables for losses in my code, I need to flip
        the signs around. The flipped rules are:
        if S < D and L < 0:
            short_term_carry = S-D
            long_term_carry = L
        elif S < D and L >= 0:
            short_term_carry = min(0, S + L - D)
            long_term_carry = 0
        elif S >= D and L < 0:
            short_term_carry = 0
            long_term_carry = min(0, L - (D-S)) = min(0, S+L-D)
        elif S >= D and L >= 0:
            short_term_carry = 0
            long_term_carry = 0
        """
        if short_term_gain < already_deducted and long_term_gain < 0:
            return ( short_term_gain - already_deducted, long_term_gain )
        elif short_term_gain < already_deducted and long_term_gain >= 0:
            return ( min(0, short_term_gain + long_term_gain - already_deducted), 0 )
        elif short_term_gain >= already_deducted and long_term_gain < 0:
            return ( 0, min(0, short_term_gain + long_term_gain - already_deducted) )
        else:
            return ( 0, 0 )

    def __get_tax_bill_or_refund_and_carryover(self):
        bill_or_refund = 0
        short_term_carryover_loss = 0
        long_term_carryover_loss = 0

        if self.total_gain_or_loss() == 0:
            bill_or_refund = 0
        elif self.total_gain_or_loss() > 0:
            """
            TODO: The following is only approximate. I should try to make it more exact
            by reading "Qualified Dividends and Capital Gain Tax Worksheet - Line 44" on
            p. 43 of http://www.irs.gov/pub/irs-pdf/i1040gi.pdf It probably subtracts
            off the income from long-term capital gains from being paid as ordinary income
            """
            if self.__accumulated_short_term_cap_gains >= 0 and self.__accumulated_long_term_cap_gains >= 0:
                bill_or_refund = self.tax_rates.short_term_cap_gains_rate_plus_state() * self.__accumulated_short_term_cap_gains + self.tax_rates.long_term_cap_gains_rate_plus_state() * self.__accumulated_long_term_cap_gains
            elif self.__accumulated_short_term_cap_gains >= 0 and self.__accumulated_long_term_cap_gains < 0:
                bill_or_refund = self.tax_rates.short_term_cap_gains_rate_plus_state() * self.total_gain_or_loss()
            elif self.__accumulated_short_term_cap_gains < 0 and self.__accumulated_long_term_cap_gains >= 0:
                bill_or_refund = self.tax_rates.long_term_cap_gains_rate_plus_state() * self.total_gain_or_loss()
            else:
                raise Exception("At least one of short or long-term gains must be > 0 to be here.")
        elif self.total_gain_or_loss() < 0:
            amount_to_deduct = max(self.total_gain_or_loss(), MAX_CAPITAL_LOSS_DEDUCTION_PER_YEAR)  # this is line 21 of Schedule D, http://www.irs.gov/pub/irs-pdf/f1040sd.pdf , except that I'm using negative numbers for losses, so I use max instead of min
            bill_or_refund = self.tax_rates.income_tax_rate_plus_state() * amount_to_deduct
            assert bill_or_refund <= 0, "We have a loss, so the tax should be negative or zero."
            (short_term_carryover_loss, long_term_carryover_loss) = self.__get_tax_carryovers(self.__accumulated_short_term_cap_gains, self.__accumulated_long_term_cap_gains, amount_to_deduct)
        return (bill_or_refund, short_term_carryover_loss, long_term_carryover_loss)

    def add_short_term_cap_gains(self, amount_to_add):
        self.__accumulated_short_term_cap_gains += amount_to_add

    def add_long_term_cap_gains(self, amount_to_add):
        self.__accumulated_long_term_cap_gains += amount_to_add

    def __set_tax_liabilities_to_zero(self):
        self.__accumulated_short_term_cap_gains = 0
        self.__accumulated_long_term_cap_gains = 0

    def total_gain_or_loss(self):
        return self.__accumulated_short_term_cap_gains + self.__accumulated_long_term_cap_gains

    def get_loss_deduction_and_carry_loss_to_next_year(self):
        assert self.total_gain_or_loss() < 0, "This method should only be called if we have a net loss!"
        loss_amount = -self.total_gain_or_loss()
        self.set_tax_liabilities_to_zero()
        if loss_amount <= MAX_CAPITAL_LOSS_DEDUCTION_PER_YEAR:
            return loss_amount
        else:
            carryforward_loss_amount = loss_amount - MAX_CAPITAL_LOSS_DEDUCTION_PER_YEAR
            self.__accumulated_long_term_cap_gains = -loss_amount
            return MAX_CAPITAL_LOSS_DEDUCTION_PER_YEAR