import Assets

EPSILON = .0001
MIN_ADDITIONAL_PURCHASE_AMOUNT = 500

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
        if broker_max_margin_to_assets_ratio <= .5:
            return broker_max_margin_to_assets_ratio * .9
        else:
            return broker_max_margin_to_assets_ratio * .8 # be more conservative when leverage is higher

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

    def margin_to_assets(self):
        if abs(self.margin-0) < .001:
            return 0
        else:
            return float(self.margin)/self.assets

    def debt_to_pay_off_to_restore_voluntary_max_margin_to_assets_ratio(self):
        """How much debt D would we need to pay off with added cash C to
        get us back to having a margin-to-assets ratio within the limit R?
        Let A be assets. If we're currently over the limit, we want to set
        C such that (D-C)/A = R  ==>  D-C = AR  ==>  C = D-AR"""
        if self.margin_to_assets() <= (1+EPSILON) * self.__personal_max_margin_to_assets_ratio:
            return 0
        else:
            return self.margin - self.assets * self.__personal_max_margin_to_assets_ratio

    def voluntary_rebalance(self, day, tax_rates):
        """Restore our voluntarily self-imposed max margin-to-assets ratio."""
        self.rebalance(day, tax_rates, self.__personal_max_margin_to_assets_ratio)

    def mandatory_rebalance(self, day, tax_rates):
        """Restore our broker-required max margin-to-assets ratio."""
        self.rebalance(day, tax_rates, self.__broker_max_margin_to_assets_ratio)

    def rebalance(self, day, tax_rates, max_margin_to_assets_ratio):
        """Restore us to a margin-to-assets ratio R within the limit (say, .5). Our 
        current margin amount is M and assets amount is A. We need to sell
        some assets to pay off some debt. To do this, we sell some amount S
        of ETF such that (M-S)/(A-S) = R  ==>  M-S = AR - SR  ==>
        M - AR = S - SR  ==>  M - AR = (1-R)S  ==>  S = (M-AR)/(1-R)"""
        if self.margin_to_assets() > (1+EPSILON) * max_margin_to_assets_ratio:
            amount_to_sell = (self.margin - self.assets * max_margin_to_assets_ratio) / (1 - max_margin_to_assets_ratio)
            self.__assets.sell(amount_to_sell, day, tax_rates)
            self.margin -= amount_to_sell
            assert self.margin_to_assets() <= (1+EPSILON) * max_margin_to_assets_ratio

    def buy_ETF(self, money_on_hand, day):
        """Say the user added M dollars. We should buy an amount of ETF
        using a loan amount of L such that L/(L+M) is the desired ratio R.
        L/(L+M) = R  ==>  L = LR + MR  ==>  L - LR = MR  ==>  L(1-R) = MR
        ==>  L = MR/(1-R)."""
        loan = money_on_hand * self.__personal_max_margin_to_assets_ratio / (1 - self.__personal_max_margin_to_assets_ratio)
        self.margin += loan
        self.__assets.buy_new_lot(money_on_hand + loan, day)
        assert self.margin_to_assets() <= (1+EPSILON) * self.__personal_max_margin_to_assets_ratio, "This assertion should also be true if the account started out within its margin limits."

    def compute_interest(self, annual_interest_rate, fraction_of_year_elapsed):
        return self.margin * ((1+annual_interest_rate)**fraction_of_year_elapsed - 1)

    def rebalance_to_increase_leverage(self, day):
        """Suppose we have margin M, assets A, and a voluntary personally
        imposed max margin-to-assets ratio R. If M/A < R, we want to 
        take out additional debt D and use it to buy more stocks such that
        (M+D)/(A+D) = R  ==>  M+D = AR+DR  ==>  M-AR = DR-D  ==>  
        M-AR = D(R-1)  ==>  D = (M-AR)/(R-1) = (AR-M)/(1-R)"""
        if self.margin_to_assets() < (1-EPSILON) * self.__personal_max_margin_to_assets_ratio:
            additional_debt = (self.assets * self.__personal_max_margin_to_assets_ratio - self.margin) / (1-self.__personal_max_margin_to_assets_ratio)
            if additional_debt >= MIN_ADDITIONAL_PURCHASE_AMOUNT: # due to transactions costs, we shouldn't bother buying new ETF shares if we only have a trivial amount of money for the purchase
                self.margin += additional_debt
                self.__assets.buy_new_lot(additional_debt, day)

    def pay_off_all_margin(self, day, tax_rates):
        assert self.assets >= self.margin, "More debt than equity!"
        self.__assets.sell(self.margin, day, tax_rates)
        self.margin = 0