import Assets
import util

EPSILON = .001
# give some wiggle room for inexact calculations, such as might result
# from not counting trading fees and stuff; for this reason, EPSILON is 
# higher than FEE_PER_DOLLAR_TRADED, defined later

MIN_ADDITIONAL_PURCHASE_AMOUNT = 50

INTERACTIVE_BROKERS_TRADING_FEE_PER_DOLLAR = .000035
"""Trading fees for Interactive Brokers are $.0035 per share
(https://www.interactivebrokers.com/en/index.php?f=commission&p=stocks2)
and currently, SPY is trading at over $200/share (http://finance.yahoo.com/q?s=SPY).
Suppose for the sake of conservatism that SPY were $100/share. Then buying/selling
$1 of SPY would be .01 shares and hence would cost $.000035 in broker fees."""

BID_ASK_EFFECTIVE_FEE_PER_DOLLAR = .0005/2
"""This parameter should be set as 1/2 the typical bid-ask spread as a fraction of total price.
As an example: For SPY, the bid-ask spread in Apr 2015 was about .01% or .0001, according to
http://www.morningstar.com/etfs/ARCX/SPY/quote.html
Suppose you buy $10,000 worth of SPY. You then turn it around and
sell it at $9,999, given the bid-ask spread. During the round trip between buying
and selling, you lost $1. In other words, the effective "fee" per dollar of transactions
was $1 / ($10,000 + $9,999), which is basically .0001/2

However, SPY is heavily traded, and most other securities have higher spreads. I calculated
for some foreign ETFs spreads of .0003, .0007, .001, and even .01 ! To average over these
different possibilities, I set the parameter as .0005/2
"""

FEE_PER_DOLLAR_TRADED = INTERACTIVE_BROKERS_TRADING_FEE_PER_DOLLAR + BID_ASK_EFFECTIVE_FEE_PER_DOLLAR


class BrokerageAccount(object):
    """Store parameters about how an investor's brokerage account"""

    def __init__(self, margin, assets, broker_max_margin_to_assets_ratio, 
                 taper_off_leverage_toward_end, 
                 initial_personal_max_margin_to_assets_relative_to_broker_max):
        self.__margin = margin # amount of debt
        self.__assets = Assets.Assets() # list of the ETFs you own
        self.__broker_max_margin_to_assets_ratio = broker_max_margin_to_assets_ratio
        self.__taper_off_leverage_toward_end = taper_off_leverage_toward_end
        self.__initial_personal_max_margin_to_assets_relative_to_broker_max = initial_personal_max_margin_to_assets_relative_to_broker_max

    def personal_max_margin_to_assets_ratio(self, years_remaining):
        """Keep a personal max margin-to-assets ratio below the broker ratio so that
        you can rebalance on your own terms rather than having the broker constantly
        force you to rebalance.
        Also, reduce leverage amount toward the end of the investing time period if 
        leverage used to be high."""
        initial_ratio_for_when_not_near_end = self.__broker_max_margin_to_assets_ratio * self.__initial_personal_max_margin_to_assets_relative_to_broker_max
        if years_remaining <= 5 and self.__taper_off_leverage_toward_end:
            two_to_one_leverage_margin_to_assets = util.N_to_1_leverage_to_max_margin_to_assets_ratio(2.0)
            return min(two_to_one_leverage_margin_to_assets, initial_ratio_for_when_not_near_end)
        elif years_remaining <= 10 and self.__taper_off_leverage_toward_end:
            three_to_one_leverage_margin_to_assets = util.N_to_1_leverage_to_max_margin_to_assets_ratio(3.0)
            return min(three_to_one_leverage_margin_to_assets, initial_ratio_for_when_not_near_end)
        else:
            return initial_ratio_for_when_not_near_end

    @property
    def margin(self):
        return self.__margin

    @margin.setter
    def margin(self, val):
        self.__margin = val

    @property
    def assets(self):
        return self.__assets.total_assets()

    def update_asset_prices(self, rate_of_return):
        self.__assets.update_prices(rate_of_return)

    def __margin_plus_positive_taxes(self, taxes):
        return self.margin + max(taxes.current_estimate_of_tax_bill_or_refund(), 0) # Don't count negative taxes because the broker doesn't count that, and we need to stay within broker limits

    def margin_to_assets(self):
        if self.assets == 0:
            return 0
        else:
            if abs(self.margin-0) < EPSILON:
                return 0
            else:
                return float(self.margin)/self.assets

    def margin_to_assets_include_tax_liabilities(self, taxes):
        """Include positive capital-gains taxes in "margin" because even if it's not owed to the
        broker now, it will come due within a year, and we need to keep an eye on it."""
        if self.assets == 0:
            return 0
        else:
            margin_plus_positive_taxes = self.__margin_plus_positive_taxes(taxes)
            if abs(margin_plus_positive_taxes-0) < EPSILON:
                return 0
            else:
                return float(margin_plus_positive_taxes)/self.assets

    def debt_to_pay_off_to_restore_voluntary_max_margin_to_assets_ratio(self, taxes, years_remaining):
        """How much debt D would we need to pay off with added cash C to
        get us back to having a margin-to-assets ratio within the limit R?
        Let A be assets. If we're currently over the limit, we want to set
        C such that (D-C)/A = R  ==>  D-C = AR  ==>  C = D-AR"""
        if self.margin_to_assets_include_tax_liabilities(taxes) <= (1+EPSILON) * self.personal_max_margin_to_assets_ratio(years_remaining):
            return 0
        else:
            return self.margin - self.assets * self.personal_max_margin_to_assets_ratio(years_remaining)

    def voluntary_rebalance(self, day, taxes, years_remaining):
        """Restore our voluntarily self-imposed max margin-to-assets ratio."""
        return self.rebalance(day, taxes, self.personal_max_margin_to_assets_ratio(years_remaining), True, True)

    def mandatory_rebalance(self, day, taxes, 
                            does_broker_liquidation_sell_tax_favored_first):
        """Restore our broker-required max margin-to-assets ratio.
        
        Interactive Brokers (IB) has a page that shows an example of how their
        margin requirements work:
        https://www.interactivebrokers.com/en/index.php?f=margin&p=overview3
        I'll show that it's equivalent to the method I'm using in this simulation,
        keeping in mind that my simulationd doesn't distinguish initial vs. 
        maintainence margin. Note that I'm also not considering 
        Special Memorandum Account (SMA) regulations yet....

        Translating IB terminology to mine:
        IB's Securities Market Value == self.assets
        IB's negative values of Cash == positive values of self.margin
        IB's Equity with Loan Value (ELV) == self.assets - self.margin
        IB talks about margin requirements opposite to how I do. I talk about maximum
            allowed margin-to-asset ratios, while IB talks about minimum allowed
            (asset-margin)/asset ratios. For example, when talking about 4X leverage,
            a person might have assets = 4, margin = 3. So I would say that's a 
            max margin-to-assets ratio of .75, while IB would say it's a ratio of .25.
            Maintaining margin/assets <= R  is equivalent to maintaining 
            -margin/assets >= -R, which is equivalent to maintaining 
            1-(margin/assets) >= 1-R, i.e., (assets-margin)/assets >= 1-R.
        IB Initial Margin (IM) and Maintenance Margin (MM) are equal in my simulation
            because I'm not distinguishing IM vs. MM amounts. Just call them M. IB says
            that for 4X leverage, M = .25 * assets. Hence, a requirement to maintain
            (assets-margin)/assets >= .25 means a requirement to maintain 
            (assets-margin) >= .25 * assets, i.e., to maintain (assets-margin) >= M.
        IB's Available Funds and Excess Liquidity are (for IM==MM) defined as ELV - M. In
            my terminology, that's (assets-margin) - (threshold for assets-margin). In other
            words, ELV - M >= 0  <==>  ELV >= M  <==>  assets-margin >= M. So maintaining
            Excess Liquidity >= 0 is equivalent to imposing the margin requirement on the 
            account in the way that I do.
        If I were writing this code over again from scratch, I probably would have used
        IB's terminology so that my wording would have been more standard.
                
        In another section ("Example: How Much Stock Do We Liquidate?") of the above-linked page,
        IB explains how they liquidate at least exactly enough funds to keep
        the account exactly in line with its margin requirements, which is the same thing I've done here.
        """
        return self.rebalance(day, taxes, self.__broker_max_margin_to_assets_ratio,
                              False, does_broker_liquidation_sell_tax_favored_first)

    def rebalance(self, day, taxes, max_margin_to_assets_ratio, include_taxes_in_margin_ratio_calculation, 
                  sell_best_for_taxes_first):
        """Restore us to a margin-to-assets ratio R within the limit (say, .5). Our 
        current margin amount is M and assets amount is A. We need to sell
        some assets to pay off some debt. To do this, we sell some amount S
        of ETF. Let the fee per dollar of S sold be F. If we sell S, we pay FS
        in fees and get S in cash to pay down margin debt. We need to set S
        such that (M-S)/(A-S-FS) = R  ==>  M-S = AR - SR - FSR  ==>
        M - AR = S - SR - FSR  ==>  M - AR = (1-R-FR)S  ==>  S = (M-AR)/(1-R-FR)"""
        deficit_still_not_paid = 0
        margin_to_assets = self.margin_to_assets_include_tax_liabilities(taxes) if include_taxes_in_margin_ratio_calculation else self.margin_to_assets()
        margin = self.__margin_plus_positive_taxes(taxes) if include_taxes_in_margin_ratio_calculation else self.margin
        num_loops = 0
        while margin_to_assets > (1+EPSILON) * max_margin_to_assets_ratio:
            """The only case where we should use this while loop more than one pass through is
            if we're including upcoming tax liabilities in the margin-to-assets calculation and
            if the process of selling securities increases those tax liabilities. This is very rare."""
            amount_of_cash_needed = (margin - self.assets * max_margin_to_assets_ratio) / (1 - max_margin_to_assets_ratio - FEE_PER_DOLLAR_TRADED * max_margin_to_assets_ratio)
            deficit_still_not_paid = self.__assets.sell(amount_of_cash_needed, FEE_PER_DOLLAR_TRADED, day, taxes, 
                               sell_best_for_taxes_first)
            if deficit_still_not_paid > 0:
                self.margin = 0 # Any remaining debt is paid off by emergency funds and becomes part of deficit to oneself
                assert self.assets == 0, "Assets aren't zero even though we ran out of assets!"
                break
            self.margin -= amount_of_cash_needed
            margin_to_assets = self.margin_to_assets_include_tax_liabilities(taxes) if include_taxes_in_margin_ratio_calculation else self.margin_to_assets()
            margin = self.__margin_plus_positive_taxes(taxes) if include_taxes_in_margin_ratio_calculation else self.margin
            num_loops += 1
            if num_loops == 10:
                print "Looped at least 10 times when trying to sell enough securities to rebalance..."
        return deficit_still_not_paid

    def buy_ETF_at_fixed_ratio(self, money_on_hand, day, years_remaining):
        """Say the user added M dollars. We should buy an amount of ETF
        using a loan amount of L such that L/(L+M) is the desired ratio R.
        L/(L+M) = R  ==>  L = LR + MR  ==>  L - LR = MR  ==>  L(1-R) = MR
        ==>  L = MR/(1-R)."""
        if money_on_hand > 0:
            loan = money_on_hand * self.personal_max_margin_to_assets_ratio(years_remaining) / (1 - self.personal_max_margin_to_assets_ratio(years_remaining))
            self.margin += loan
            self.__assets.buy_new_lot(money_on_hand + loan, FEE_PER_DOLLAR_TRADED, day)
            # This is no longer true:   assert self.margin_to_assets() <= (1+EPSILON) * self.personal_max_margin_to_assets_ratio(years_remaining), "This assertion should also be true if the account started out within its margin limits."

    def buy_ETF_without_margin(self, money_on_hand, day):
        if money_on_hand > 0:
            self.__assets.buy_new_lot(money_on_hand, FEE_PER_DOLLAR_TRADED, day)

    def compute_interest(self, annual_interest_rate, fraction_of_year_elapsed):
        return self.margin * ((1+annual_interest_rate)**fraction_of_year_elapsed - 1)

    def voluntary_rebalance_to_increase_leverage(self, day, taxes, years_remaining):
        """Suppose we have margin M, assets A, and a voluntary personally
        imposed max margin-to-assets ratio R. If M/A < R, we want to 
        take out additional debt D and use it to buy more stocks such that
        (M+D)/(A+D) = R  ==>  M+D = AR+DR  ==>  M-AR = DR-D  ==>  
        M-AR = D(R-1)  ==>  D = (M-AR)/(R-1) = (AR-M)/(1-R)"""
        if self.assets > 0:
            if self.margin_to_assets_include_tax_liabilities(taxes) < (1-EPSILON) * self.personal_max_margin_to_assets_ratio(years_remaining):
                additional_debt = (self.assets * self.personal_max_margin_to_assets_ratio(years_remaining) - self.__margin_plus_positive_taxes(taxes)) / (1-self.personal_max_margin_to_assets_ratio(years_remaining))
                if additional_debt >= MIN_ADDITIONAL_PURCHASE_AMOUNT: # due to transactions costs, we shouldn't bother buying new ETF shares if we only have a trivial amount of money for the purchase
                    self.margin += additional_debt
                    self.__assets.buy_new_lot(additional_debt, FEE_PER_DOLLAR_TRADED, day)

    def tax_loss_harvest(self, day, taxes):
        cash_earned = self.__assets.tax_loss_harvest(FEE_PER_DOLLAR_TRADED, day, taxes) # sell capital-loss lots
        if cash_earned > 0:
            self.__assets.buy_new_lot(cash_earned, FEE_PER_DOLLAR_TRADED, day) # buy new lot
            """IN REAL LIFE, THE INVESTOR WOULD HAVE TO WAIT 30 DAYS TO 
            AVOID A WASH SALE! http://www.investopedia.com/terms/w/washsalerule.asp
            I'm ignoring that here for simplicity."""

    def pay_off_all_margin(self, day, taxes):
        assert self.assets >= self.margin, "More debt than equity!"
        deficit_still_not_paid = self.__assets.sell(self.margin, FEE_PER_DOLLAR_TRADED, day, taxes, True)
        self.margin = 0
        return deficit_still_not_paid