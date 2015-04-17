import Assets

EPSILON = .0001
MIN_ADDITIONAL_PURCHASE_AMOUNT = 500
FEE_PER_DOLLAR_TRADED = .000035
"""Trading fees for Interactive Brokers are $.0035 per share
(https://www.interactivebrokers.com/en/index.php?f=commission&p=stocks2)
and currently, SPY is trading at over $200/share (http://finance.yahoo.com/q?s=SPY).
Suppose for the sake of conservatism that SPY were $100/share. Then buying/selling
$1 of SPY would be .01 shares and hence would cost $.000035 in broker fees."""

class BrokerageAccount(object):
    """Store parameters about how an investor's brokerage account"""

    def __init__(self, margin, assets, broker_max_margin_to_assets_ratio):
        self.__margin = margin # amount of debt
        self.__assets = Assets.Assets() # list of the ETFs you own
        self.__broker_max_margin_to_assets_ratio = broker_max_margin_to_assets_ratio
        self.__personal_max_margin_to_assets_ratio = self.personal_ratio_given_broker_ratio(self.__broker_max_margin_to_assets_ratio)

    def personal_ratio_given_broker_ratio(self, broker_max_margin_to_assets_ratio):
        """Keep a personal max margin-to-assets ratio below the broker ratio so that
        you can rebalance on your own terms rather than having the broker constantly
        force you to rebalance."""
        return broker_max_margin_to_assets_ratio * .9
        """
        if broker_max_margin_to_assets_ratio <= .5:
            return broker_max_margin_to_assets_ratio * .9
        else:
            return broker_max_margin_to_assets_ratio * .9 # be more conservative when leverage is higher
        """

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

    def margin_to_assets(self, taxes):
        """Include positive capital-gains taxes in "margin" because even if it's not owed to the
        broker now, it will come due within a year, and we need to keep an eye on it."""
        margin_plus_positive_taxes = self.__margin_plus_positive_taxes(taxes)
        if abs(margin_plus_positive_taxes-0) < EPSILON:
            return 0
        else:
            return float(margin_plus_positive_taxes)/self.assets

    def debt_to_pay_off_to_restore_voluntary_max_margin_to_assets_ratio(self, taxes):
        """How much debt D would we need to pay off with added cash C to
        get us back to having a margin-to-assets ratio within the limit R?
        Let A be assets. If we're currently over the limit, we want to set
        C such that (D-C)/A = R  ==>  D-C = AR  ==>  C = D-AR"""
        if self.margin_to_assets(taxes) <= (1+EPSILON) * self.__personal_max_margin_to_assets_ratio:
            return 0
        else:
            return self.margin - self.assets * self.__personal_max_margin_to_assets_ratio

    def voluntary_rebalance(self, day, taxes):
        """Restore our voluntarily self-imposed max margin-to-assets ratio."""
        self.rebalance(day, taxes, self.__personal_max_margin_to_assets_ratio)

    def mandatory_rebalance(self, day, taxes):
        """Restore our broker-required max margin-to-assets ratio."""
        self.rebalance(day, taxes, self.__broker_max_margin_to_assets_ratio)

    def rebalance(self, day, taxes, max_margin_to_assets_ratio):
        """Restore us to a margin-to-assets ratio R within the limit (say, .5). Our 
        current margin amount is M and assets amount is A. We need to sell
        some assets to pay off some debt. To do this, we sell some amount S
        of ETF. Let the fee per dollar of S sold be F. If we sell S, we pay FS
        in fees and get S in cash to pay down margin debt. We need to set S
        such that (M-S)/(A-S-FS) = R  ==>  M-S = AR - SR - FSR  ==>
        M - AR = S - SR - FSR  ==>  M - AR = (1-R-FR)S  ==>  S = (M-AR)/(1-R-FR)"""
        if self.margin_to_assets(taxes) > (1+EPSILON) * max_margin_to_assets_ratio:
            amount_of_cash_needed = (self.__margin_plus_positive_taxes(taxes) - self.assets * max_margin_to_assets_ratio) / (1 - max_margin_to_assets_ratio - FEE_PER_DOLLAR_TRADED * max_margin_to_assets_ratio)
            # rough amount to sell may differ from actual amount sold because
            # there can be tax breaks from selling losses (which I unrealistically
            # but for simplicity assume are taken immediately rather than at 
            # tax time next year)
            self.__assets.sell(amount_of_cash_needed, FEE_PER_DOLLAR_TRADED, day, taxes)
            self.margin -= amount_of_cash_needed
            assert self.margin_to_assets(taxes) <= (1+EPSILON) * max_margin_to_assets_ratio

    def buy_ETF_at_fixed_ratio(self, money_on_hand, day):
        """Say the user added M dollars. We should buy an amount of ETF
        using a loan amount of L such that L/(L+M) is the desired ratio R.
        L/(L+M) = R  ==>  L = LR + MR  ==>  L - LR = MR  ==>  L(1-R) = MR
        ==>  L = MR/(1-R)."""
        if money_on_hand > 0:
            loan = money_on_hand * self.__personal_max_margin_to_assets_ratio / (1 - self.__personal_max_margin_to_assets_ratio)
            self.margin += loan
            self.__assets.buy_new_lot(money_on_hand + loan, FEE_PER_DOLLAR_TRADED, day)
            # This is no longer true:   assert self.margin_to_assets() <= (1+EPSILON) * self.__personal_max_margin_to_assets_ratio, "This assertion should also be true if the account started out within its margin limits."

    def buy_ETF_without_margin(self, money_on_hand, day):
        if money_on_hand > 0:
            self.__assets.buy_new_lot(money_on_hand, FEE_PER_DOLLAR_TRADED, day)

    def compute_interest(self, annual_interest_rate, fraction_of_year_elapsed):
        return self.margin * ((1+annual_interest_rate)**fraction_of_year_elapsed - 1)

    def rebalance_to_increase_leverage(self, day, taxes):
        """Suppose we have margin M, assets A, and a voluntary personally
        imposed max margin-to-assets ratio R. If M/A < R, we want to 
        take out additional debt D and use it to buy more stocks such that
        (M+D)/(A+D) = R  ==>  M+D = AR+DR  ==>  M-AR = DR-D  ==>  
        M-AR = D(R-1)  ==>  D = (M-AR)/(R-1) = (AR-M)/(1-R)"""
        if self.margin_to_assets(taxes) < (1-EPSILON) * self.__personal_max_margin_to_assets_ratio:
            additional_debt = (self.assets * self.__personal_max_margin_to_assets_ratio - self.__margin_plus_positive_taxes(taxes)) / (1-self.__personal_max_margin_to_assets_ratio)
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
        self.__assets.sell(self.margin, FEE_PER_DOLLAR_TRADED, day, taxes)
        self.margin = 0