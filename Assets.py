import operator
import random
import util
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
        lots_to_delete_because_lost_all_value = []
        for lot in self.__lots_list:
            if lot.update_price(rate_of_return):
                lots_to_delete_because_lost_all_value.append(lot)
        for lot_to_delete in lots_to_delete_because_lost_all_value:
            self.__lots_list.remove(lot_to_delete)

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
        to sell more than C of actual ETFs.
        """
        deficit_still_not_paid = 0
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
            if self.__lots_list:
                (cash_still_need_to_get, lot_emptied) = self.__lots_list[0].sell(
                    cash_still_need_to_get, fee_per_dollar_traded, day, taxes)
                if lot_emptied:
                    self.__lots_list.pop(0)
            else: # list is empty; we have no more securities, but we need cash!
                deficit_still_not_paid = cash_still_need_to_get
                print "Account wiped out with %s still needing to be repaid." % util.format_as_dollar_string(cash_still_need_to_get) ,
                assert self.total_assets() == 0, "Total assets aren't 0 despite wiping out all assets."
                break
        
        """If you have a deficit that isn't yet paid, you tap into other savings
        you may have in order to pay for it. 
        I assume the other savings have long-term maturity. 
        Much of their value may be as capital gains rather than principal.
        It's not clear what amount of them will be capital gains vs. what amount
        are cost basis. As a compromise, I assume half of the amount of equity 
        is in capital gains (since you can choose to sell those securities with
        less capital gains first).
        So the increase in your long-term capital gains is half of the amount
        you sell."""
        taxes.add_long_term_cap_gains(deficit_still_not_paid/2)
        return deficit_still_not_paid

    def tax_loss_harvest(self, fee_per_dollar_traded, day, taxes):
        lots_to_harvest = [lot for tax, lot in self.__get_sorted_tax_rates_and_lots(day, taxes) if tax < 0]
        self.__lots_list = [lot for tax, lot in self.__get_sorted_tax_rates_and_lots(day, taxes) if tax >= 0] # only keep the remainder that aren't harvested
        return sum([lot.harvest(fee_per_dollar_traded, day, taxes) for lot in lots_to_harvest]) # total earnings from selling the securities
            