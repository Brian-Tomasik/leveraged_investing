import operator
import random
import EtfLot

class Assets(object):
    """Stores the collection of ETF lots that the investor holds"""

    def __init__(self):
        self.__lots_list = []

    def buy_new_lot(self, purchase_amount, fee_per_dollar_traded, day):
        self.__lots_list.append(EtfLot.EtfLot(purchase_amount, fee_per_dollar_traded, day))

    def total_assets(self):
        total = 0
        for lot in self.__lots_list:
            total += lot.current_price
        return total

    def update_prices(self, rate_of_return):
        for lot in self.__lots_list:
            lot.update_price(rate_of_return)

    def __get_sorted_tax_rates_and_lots(self, day, taxes):
        """Sort lots by most-tax-advantaged-to-sell first"""
        list_to_sort = [(lot.capital_gains_tax_rate(day, taxes.tax_rates), lot) for lot in self.__lots_list]
        list_to_sort.sort(key=operator.itemgetter(0))
        return list_to_sort

    def sell(self, amount_of_net_cash_to_get_back, fee_per_dollar_traded, day, taxes, 
             sell_best_for_taxes_first):
        """If sell_best_for_taxes_first is True, sort lots according to which ones, 
        if sold, incur least capital-gains tax. Otherwise sort randomly.
        Since we're paying taxes, in order to get C dollars of after-tax cash back, we need 
        to sell more than C of actual ETFs."""
        if sell_best_for_taxes_first:
            # Sort to put ETFs that would incur lowest capital-gains taxes first.
            # Use decorate-sort-undecorate pattern because too complicated to use
            # the capital_gains_tax function as a sort key.
            self.__lots_list = [lot for tax, lot in self.__get_sorted_tax_rates_and_lots(day, taxes)]
        else:
            random.shuffle(self.__lots_list)

        # get cash
        cash_still_need_to_get = amount_of_net_cash_to_get_back
        while cash_still_need_to_get > 0:
            (cash_still_need_to_get, lot_emptied) = self.__lots_list[0].sell(
                cash_still_need_to_get, fee_per_dollar_traded, day, taxes)
            if lot_emptied:
                self.__lots_list.pop(0)

    def tax_loss_harvest(self, fee_per_dollar_traded, day, taxes):
        lots_to_harvest = [lot for tax, lot in self.__get_sorted_tax_rates_and_lots(day, taxes) if tax < 0]
        self.__lots_list = [lot for tax, lot in self.__get_sorted_tax_rates_and_lots(day, taxes) if tax >= 0] # only keep the remainder that aren't harvested
        return sum([lot.harvest(fee_per_dollar_traded, day, taxes) for lot in lots_to_harvest]) # total earnings from selling the securities
            