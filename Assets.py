import operator
import EtfLot

class Assets(object):
    """Stores the collection of ETF lots that the investor holds"""

    def __init__(self):
        self.__lots_list = []

    def buy_new_lot(self, purchase_amount, day):
        self.__lots_list.append(EtfLot.EtfLot(purchase_amount, day))

    def total_assets(self):
        total = 0
        for lot in self.__lots_list:
            total += lot.current_price
        return total

    def update_prices(self, rate_of_return):
        for lot in self.__lots_list:
            lot.update_price(rate_of_return)

    def sell(self, amount_of_net_cash_to_get_back, day, tax_rates):
        """Sort lots according to which ones, if sold, incur least capital-gains tax.
        Since we're paying taxes, in order to get C dollars of after-tax cash back, we need 
        to sell more than C of actual ETFs."""
        # Sort to put ETFs that would incur lowest capital-gains taxes first.
        # Use decorate-sort-undecorate pattern because too complicated to use
        # the capital_gains_tax function as a sort key.
        list_to_sort = [(lot.capital_gains_tax(day, tax_rates), lot) for lot in self.__lots_list]
        list_to_sort.sort(key=operator.itemgetter(0))
        self.__lots_list = [lot for tax, lot in list_to_sort]

        # get cash
        cash_still_need_to_get = amount_of_net_cash_to_get_back
        while cash_still_need_to_get > 0:
            (cash_still_need_to_get, lot_emptied) = self.__lots_list[0].sell(
                cash_still_need_to_get, day, tax_rates)
            if lot_emptied:
                self.__lots_list.pop(0)