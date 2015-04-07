EPSILON = 0

class BrokerageAccount(object):
    """Store parameters about how an investor's brokerage account"""

    def __init__(self, margin, assets, margin_to_assets_when_buy_new_stock,
                 max_margin_to_assets_ratio):
        self.__margin = margin # amount of debt
        self.__assets = assets # value of the stocks you own
        self.__margin_to_assets_when_buy_new_stock = margin_to_assets_when_buy_new_stock
        self.__max_margin_to_assets_ratio = max_margin_to_assets_ratio
        assert self.__margin_to_assets_when_buy_new_stock <= self.max_margin_to_assets_ratio, "Based on how I'm implementing this particular program, I'm not letting you buy with leverage beyond the max leverage rate for the overall account even if you could theoretically due to having enough assets already in the account."

    @property
    def margin(self):
        return self.__margin

    @margin.setter
    def margin(self, val):
        self.__margin = val

    @property
    def assets(self):
        return self.__assets

    @property
    def max_margin_to_assets_ratio(self):
        return self.__max_margin_to_assets_ratio

    @assets.setter
    def assets(self, val):
        self.__assets = val

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

    def margin_call_rebalance(self):
        """Restore us to a margin-to-assets ratio R within the limit (say, .5). Our 
        current margin amount is M and assets amount is A. We need to sell
        some assets to pay off some debt. To do this, we sell some amount S
        of stock such that (M-S)/(A-S) = R  ==>  M-S = AR - SR  ==>
        M - AR = S - SR  ==>  M - AR = (1-R)S  ==>  S = (M-AR)/(1-R)"""
        if self.margin_to_assets() > (1+EPSILON) * self.max_margin_to_assets_ratio:
            amount_to_sell = (self.margin - self.assets * self.max_margin_to_assets_ratio) / (1 - self.max_margin_to_assets_ratio)
            self.assets -= amount_to_sell
            self.margin -= amount_to_sell
            assert self.margin_to_assets() <= (1+EPSILON) * self.max_margin_to_assets_ratio

    def buy_stock(self, money_on_hand):
        """Say the user added M dollars. We should buy an amount of stock
        using a loan amount of L such that L/(L+M) is the desired ratio R.
        L/(L+M) = R  ==>  L = LR + MR  ==>  L - LR = MR  ==>  L(1-R) = MR
        ==>  L = MR/(1-R)."""
        loan = money_on_hand * self.__margin_to_assets_when_buy_new_stock / (1 - self.__margin_to_assets_when_buy_new_stock)
        self.margin += loan
        self.assets += money_on_hand + loan
        assert self.margin_to_assets() <= (1+EPSILON) * self.max_margin_to_assets_ratio, "This assertion should also be true if the account started out within its margin limits."

    def compute_interest(self, annual_interest_rate, fraction_of_year_elapsed):
        return self.margin * ((1+annual_interest_rate)**fraction_of_year_elapsed - 1)

    def pay_off_all_margin(self):
        assert self.assets >= self.margin, "More debt than equity!"
        self.assets -= self.margin
        self.margin = 0