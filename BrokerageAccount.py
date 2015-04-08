import Assets

EPSILON = 0

class BrokerageAccount(object):
    """Store parameters about how an investor's brokerage account"""

    def __init__(self, margin, assets, margin_to_assets_when_buy_new_ETF,
                 max_margin_to_assets_ratio):
        self.__margin = margin # amount of debt
        self.__assets = Assets.Assets() # list of the ETFs you own
        self.__margin_to_assets_when_buy_new_ETF = margin_to_assets_when_buy_new_ETF
        self.__max_margin_to_assets_ratio = max_margin_to_assets_ratio
        assert self.__margin_to_assets_when_buy_new_ETF <= self.max_margin_to_assets_ratio, "Based on how I'm implementing this particular program, I'm not letting you buy with leverage beyond the max leverage rate for the overall account even if you could theoretically due to having enough assets already in the account."

    @property
    def margin(self):
        return self.__margin

    @margin.setter
    def margin(self, val):
        self.__margin = val

    @property
    def assets(self):
        return self.__assets.total_assets()

    @property
    def max_margin_to_assets_ratio(self):
        return self.__max_margin_to_assets_ratio

    def update_asset_prices(self, rate_of_return):
        self.__assets.update_prices(rate_of_return)

    def margin_to_assets(self):
        if abs(self.margin-0) < .001:
            return 0
        else:
            return float(self.margin)/self.assets

    def debt_to_pay_off_for_margin_call(self):
        """How much debt D would we need to pay off with added cash C to
        get us back to having a margin-to-assets ratio within the limit R?
        Let A be assets. If we're currently over the limit, we want to set
        C such that (D-C)/A = R  ==>  D-C = AR  ==>  C = D-AR"""
        if self.margin_to_assets() <= (1+EPSILON) * self.max_margin_to_assets_ratio:
            return 0
        else:
            return self.margin - self.assets * self.max_margin_to_assets_ratio

    def margin_call_rebalance(self, day, short_term_cap_gains_rate, long_term_cap_gains_rate):
        """Restore us to a margin-to-assets ratio R within the limit (say, .5). Our 
        current margin amount is M and assets amount is A. We need to sell
        some assets to pay off some debt. To do this, we sell some amount S
        of ETF such that (M-S)/(A-S) = R  ==>  M-S = AR - SR  ==>
        M - AR = S - SR  ==>  M - AR = (1-R)S  ==>  S = (M-AR)/(1-R)"""
        if self.margin_to_assets() > (1+EPSILON) * self.max_margin_to_assets_ratio:
            amount_to_sell = (self.margin - self.assets * self.max_margin_to_assets_ratio) / (1 - self.max_margin_to_assets_ratio)
            self.__assets.sell(amount_to_sell, day, short_term_cap_gains_rate, long_term_cap_gains_rate)
            self.margin -= amount_to_sell
            assert self.margin_to_assets() <= (1+EPSILON) * self.max_margin_to_assets_ratio

    def buy_ETF(self, money_on_hand, day):
        """Say the user added M dollars. We should buy an amount of ETF
        using a loan amount of L such that L/(L+M) is the desired ratio R.
        L/(L+M) = R  ==>  L = LR + MR  ==>  L - LR = MR  ==>  L(1-R) = MR
        ==>  L = MR/(1-R)."""
        loan = money_on_hand * self.__margin_to_assets_when_buy_new_ETF / (1 - self.__margin_to_assets_when_buy_new_ETF)
        self.margin += loan
        self.__assets.buy_new_lot(money_on_hand + loan, day)
        assert self.margin_to_assets() <= (1+EPSILON) * self.max_margin_to_assets_ratio, "This assertion should also be true if the account started out within its margin limits."

    def compute_interest(self, annual_interest_rate, fraction_of_year_elapsed):
        return self.margin * ((1+annual_interest_rate)**fraction_of_year_elapsed - 1)

    def pay_off_all_margin(self, day, short_term_cap_gains_rate, long_term_cap_gains_rate):
        assert self.assets >= self.margin, "More debt than equity!"
        self.__assets.sell(self.margin, day, short_term_cap_gains_rate, long_term_cap_gains_rate)
        self.margin = 0