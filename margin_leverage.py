import util
import plots
import write_results
import Investor
import Market
import BrokerageAccount
import TaxRates
import Taxes
import numpy
import copy
import math
import os
from os import path
from multiprocessing import Process, Queue
import time
from random import Random

USE_SMALL_SCENARIO_SET_FOR_QUICK_TEST = True
if USE_SMALL_SCENARIO_SET_FOR_QUICK_TEST:
    SCENARIOS = {"Personal max margin is broker max":"persmaxbrokermax"}
    #"No unemployment or inflation or taxes or black swans, only paid in first month, don't taper off leverage toward end, voluntary max leverage equals broker max leverage, no emergency savings":"closetotheory"}
    """
                "No unemployment or inflation or taxes or black swans, don't taper off leverage toward end, voluntary max leverage equals broker max leverage, no emergency savings":"closetotheoryminus1",
                 "No unemployment or inflation or taxes or black swans, don't taper off leverage toward end, no emergency savings":"closetotheoryminus2",
                 "No unemployment or inflation or taxes or black swans, no emergency savings":"closetotheoryminus3",
                 "No unemployment or inflation or taxes, no emergency savings":"closetotheoryminus4",
                 "No unemployment or inflation, no emergency savings":"closetotheoryminus5",
                 "No unemployment, no emergency savings":"closetotheoryminus6",
                 "No emergency savings":"closetotheoryminus7"}"""
else:
    SCENARIOS = {"No unemployment or inflation or taxes or black swans, only paid in first month, don't taper off leverage toward end, voluntary max leverage equals broker max leverage, no emergency savings":"closetotheory",
                 "Default":"default",
                 "No unemployment or inflation or taxes or black swans, don't taper off leverage toward end, voluntary max leverage equals broker max leverage, no emergency savings":"closetotheoryminus1",
                 "No unemployment or inflation or taxes or black swans, don't taper off leverage toward end, no emergency savings":"closetotheoryminus2",
                 "No unemployment or inflation or taxes or black swans, no emergency savings":"closetotheoryminus3",
                 "No unemployment or inflation or taxes, no emergency savings":"closetotheoryminus4",
                 "No unemployment or inflation, no emergency savings":"closetotheoryminus5",
                 "No unemployment, no emergency savings":"closetotheoryminus6",
                 "No emergency savings":"closetotheoryminus7",
                 "Emergency savings = $1 million":"emergsav1m",
                 "Don't rebalance monthly":"dontreb",
                 "Favored tax ordering when liquidate":"FO",
                 "Use VIX data":"VIX",
                 "Pay down principal throughout investment period":"princthru",
                 "Annual sigma = .4":"sig4",
                 "Annual sigma = 0":"sig0",
                 "Annual mu = .1":"mu10",
                 "Annual mu = .1, don't rebalance monthly":"mu10dontreb",
                 "Annual mu = .07":"mu07",
                 "Annual mu = .04":"mu04",
                 "Annual mu = -.02":"mu02minus",
                 "Annual margin interest rate = .015":"int_r015",
                 "Donate after 5 years":"yrs5",
                 "Donate after 30 years":"yrs30",
                 "Don't taper off leverage toward end":"donttaper",
                 "Don't rebalance monthly and don't taper off leverage toward end":"dontrebtaper",
                 "Personal max margin is broker max":"persmaxbrokermax"}

DAYS_PER_YEAR = 365
TAX_LOSS_HARVEST_DAY = 360 # day number 360 in late Dec
TAX_DAY = 60 # day of tax payments/refund assuming you get your refund around March 1; ignoring payments during the year...
TINY_NUMBER = .000001
THRESHOLD_FOR_TAX_CONVERGENCE = 50
DIFFERENCE_THRESHOLD_FOR_WARNING_ABOUT_DIFF_FROM_SIMPLE_COMPUTATION_PER_YEAR = .05
TYPES = ["regular", "margin", "matched401k"]
NUM_PERCENT_DIFFS_TO_PLOT = 10
INTEREST_AND_SALARY_EVERY_NUM_DAYS = 30

def one_run(investor,market,verbosity,outfilepath,iter_num,
            num_margin_trajectories_to_save_as_figures, randgenerator):
    investor.reset_employment_for_next_round()
    days_from_start_to_donation_date = int(DAYS_PER_YEAR * investor.years_until_donate)
    accounts = dict()
    accounts["regular"] = BrokerageAccount.BrokerageAccount(0,0,0,investor.taper_off_leverage_toward_end,investor.initial_personal_max_margin_to_assets_relative_to_broker_max)
    accounts["margin"] = BrokerageAccount.BrokerageAccount(0,0,investor.broker_max_margin_to_assets_ratio,investor.taper_off_leverage_toward_end,investor.initial_personal_max_margin_to_assets_relative_to_broker_max)
    accounts["matched401k"] = BrokerageAccount.BrokerageAccount(0,0,0,investor.taper_off_leverage_toward_end,investor.initial_personal_max_margin_to_assets_relative_to_broker_max)
    debt_to_yourself_after_margin_account_lost_all_value = 0
    """Non-margin investors can't get into debt, so we need only track debt to yourself
    for the margin-investing case. This variable assumes that if you go into the hole with
    a margin account, you have other emergency assets that you use to pay that debt. Then
    this variable records how many of those emergency assets you used up, which means you're
    not getting to invest them in the market. Hence, this is like a debt you borrow from yourself
    that you need to pay off over time by replenishing your emergency fund."""
    margin_strategy_went_bankrupt = False
    num_times_randgenerator_was_called = 0
    PRINT_DEBUG_STUFF = False

    taxes = dict()
    emergency_savings = dict()
    simple_approx_account_values = dict()
    for type in TYPES:
        taxes[type] = Taxes.Taxes(investor.tax_rates)
        emergency_savings[type] = investor.initial_emergency_savings
        simple_approx_account_values[type] = 0
    interest_and_salary_every_fraction_of_year = float(INTEREST_AND_SALARY_EVERY_NUM_DAYS) / DAYS_PER_YEAR

    # Record history over lifetime of investment
    historical_margin_to_assets_ratios = numpy.zeros(days_from_start_to_donation_date)
    historical_regular_wealth = numpy.zeros(days_from_start_to_donation_date)
    historical_margin_wealth = numpy.zeros(days_from_start_to_donation_date)
    historical_carried_cap_gains = numpy.zeros(days_from_start_to_donation_date)
    historical_margin_percent_differences_from_simple_calc = numpy.zeros(days_from_start_to_donation_date)

    for day in xrange(days_from_start_to_donation_date):
        years_elapsed = day/DAYS_PER_YEAR # intentional int division
        years_remaining = (days_from_start_to_donation_date-day)/DAYS_PER_YEAR

        # Record historical info for future reference
        cur_margin_to_assets = accounts["margin"].margin_to_assets()
        historical_margin_to_assets_ratios[day] = cur_margin_to_assets if cur_margin_to_assets is not float("inf") else 0
        historical_regular_wealth[day] = accounts["regular"].assets_minus_margin() + emergency_savings["regular"]
        historical_margin_wealth[day] = accounts["margin"].assets_minus_margin() + emergency_savings["margin"]
        historical_carried_cap_gains[day] = taxes["margin"].total_gain_or_loss()

        # Check deviations from simple approximate estimates of account values
        for type in TYPES:
            actual_value = accounts[type].assets_minus_margin()
            difference = util.fractional_difference(actual_value, simple_approx_account_values[type])
            if type is not "margin":
                assert abs(difference) < TINY_NUMBER, "Non-margin simple calculations should match the real things."
            else:
                historical_margin_percent_differences_from_simple_calc[day] = \
                    100*difference if difference is not float("inf") else 100 # just turn infinity into 100% difference
                if abs(difference) > DIFFERENCE_THRESHOLD_FOR_WARNING_ABOUT_DIFF_FROM_SIMPLE_COMPUTATION_PER_YEAR * \
                    investor.years_until_donate:
                    if difference == float("inf"):
                        percent_diff_string = "infinity"
                    else:
                        percent_diff_string = str(int(round(100*difference,0)))
                    print "WARNING: Actual account value (%s) differs by %s percent from simple approximate value (%s)." % \
                        (util.format_as_dollar_string(actual_value), percent_diff_string, \
                        util.format_as_dollar_string(simple_approx_account_values[type]))

        """ Stock market changes on non-holiday weekdays.
        The functions to check if it's a weekend and a holiday are based on the year
        2015, when all holidays should have been non-weekends. This means there are
        9 non-weekend holidays. Thus, the number of trading days in the year is
        365 * 5/7 - 9 = 252, which is what we wanted. Probably it's not actually important
        that I'm keeping track of what exact day of the year it is here, but 
        oh well. :)"""
        if not util.day_is_weekend(day % DAYS_PER_YEAR) and not util.day_is_holiday(day % DAYS_PER_YEAR):
            (random_daily_return, num_times_randgenerator_was_called) = \
                market.random_daily_return(day, randgenerator, num_times_randgenerator_was_called)
            if PRINT_DEBUG_STUFF and iter_num == 1:
                print "today return = %f" % random_daily_return

            for type in TYPES:
                # Update emergency savings
                (emergency_savings[type], price_went_to_zero) = \
                    util.update_price(emergency_savings[type], random_daily_return)
                # Update simple approximations to account values
                cur_leverage_multiple = util.max_margin_to_assets_ratio_to_N_to_1_leverage( \
                    accounts[type].personal_max_margin_to_assets_ratio(years_remaining)) if \
                    investor.rebalance_monthly_to_increase_leverage else \
                    util.max_margin_to_assets_ratio_to_N_to_1_leverage( \
                    accounts[type].margin_to_assets())
                """The above if/else thing is because if we're rebalancing up towards a desired
                leverage ratio, we want to check that future account values are consistent with that
                desired leverage ratio. If we're not tracking a given leverage ratio because we're
                not rebalancing monthly, then the calculation of simple account values should just
                use the actual current margin-to-assets ratio, since there's no alternative but
                to use that."""
                if type is not "margin":
                    assert cur_leverage_multiple == 1.0, "Non-leveraged methods shouldn't have non-1 leverage multiples."
                if margin_strategy_went_bankrupt:
                    cur_leverage_multiple = 1.0
                    """When it goes bankrupt, the margin strategy stops using margin, so
                    its leverage multiple should be 1.0 at that point."""
                simple_approx_account_values[type] *= (1+cur_leverage_multiple*random_daily_return \
                    - (cur_leverage_multiple-1.0)*market.annual_margin_interest_rate/market.trading_days_per_year)
                if simple_approx_account_values[type] < 0:
                    simple_approx_account_values[type] = 0

            # Update regular account
            accounts["regular"].update_asset_prices(random_daily_return)

            # Update margin account
            if emergency_savings["margin"] < emergency_savings["regular"]:
                assert accounts["margin"].assets == 0, "We should only have tapped into emergency savings if we lost all margin-invested assets!"
                assert accounts["margin"].margin == 0, "If we have no assets, we also shouldn't have margin in the account. Instead, we ate into emergency savings or went bankrupt."
            else:
                accounts["margin"].update_asset_prices(random_daily_return)
                deficit_still_not_paid = accounts["margin"].mandatory_rebalance(
                    day, taxes["margin"], investor.does_broker_liquidation_sell_tax_favored_first)
                """Interactive Brokers (IB) forces you to stay within the mandated
                margin-to-assets ratio, (I think) on a day-by-day basis. The above
                function call simulates IB selling any positions
                as needed to restore the margin-to-assets ratio. Because IB
                is so strict about staying within the limits, the margin investor
                in this simulation voluntarily maintains a max margin-to-assets
                ratio somewhat below the broker-imposed limit."""
                (emergency_savings, accounts, margin_strategy_went_bankrupt) = \
                     check_if_margin_strategy_should_use_emergency_funds_and_maybe_go_bankrupt(
                         deficit_still_not_paid, emergency_savings, accounts, investor)

            # Update matched 401k account
            accounts["matched401k"].update_asset_prices(random_daily_return)

        # check if we should get paid and defray interest
        if day % INTEREST_AND_SALARY_EVERY_NUM_DAYS == 0:
            pay = investor.current_annual_income(years_elapsed, day, market.inflation_rate) * \
                (float(INTEREST_AND_SALARY_EVERY_NUM_DAYS) / DAYS_PER_YEAR)
            
            if verbosity > 1:
                if day % 1000 == 0:
                    print "Day " + str(day) + ", year " + str(years_elapsed)

            # regular account just buys ETF
            accounts["regular"].buy_ETF_at_fixed_ratio(pay, day, years_remaining)
            simple_approx_account_values["regular"] += pay * (1-BrokerageAccount.FEE_PER_DOLLAR_TRADED)

            # matched 401k account buys ETF with employee and employer funds
            matched_pay_amount = pay * (1+investor.match_percent_from_401k/100.0)
            accounts["matched401k"].buy_ETF_at_fixed_ratio(matched_pay_amount, day, years_remaining)
            simple_approx_account_values["matched401k"] += matched_pay_amount * (1-BrokerageAccount.FEE_PER_DOLLAR_TRADED)

            simple_approx_account_values["margin"] += pay * (1-BrokerageAccount.FEE_PER_DOLLAR_TRADED)
            if margin_strategy_gap_in_emergency_funds(emergency_savings) > pay:
                # restore emergency savings with pay
                emergency_savings["margin"] += pay
                assert accounts["margin"].margin == 0, "We shouldn't have margin debt if we're in this branch."
                assert accounts["margin"].assets == 0, "We shouldn't have assets if we're in this branch."
            else:
                # The next steps are for the margin account. It
                # 0. pays debt to itself if any
                # 1. pays interest
                # 2. pays some principal on loans
                # 3. pay down margin if it's over limit
                # 4. buys new ETF with the remaining $

                # 0. restore any needed emergency savings
                if margin_strategy_gap_in_emergency_funds(emergency_savings) > 0:
                    pay -= margin_strategy_gap_in_emergency_funds(emergency_savings)
                    emergency_savings["margin"] += margin_strategy_gap_in_emergency_funds(emergency_savings)
                    assert emergency_savings["margin"] == emergency_savings["regular"], "Margin's emergency savings should have been restored to equality with regular's emergency savings here."

                # 1. pay interest
                interest = accounts["margin"].compute_interest(market.annual_margin_interest_rate,
                                                               interest_and_salary_every_fraction_of_year)
                pay_after_interest = pay - interest
                if pay_after_interest <= 0:
                    accounts["margin"].margin += (interest - pay) # amount of interest remaining
                    deficit_still_not_paid = accounts["margin"].voluntary_rebalance(
                        day, taxes["margin"], years_remaining) # pay for the interest with equity
                    (emergency_savings, accounts, margin_strategy_went_bankrupt) = \
                         check_if_margin_strategy_should_use_emergency_funds_and_maybe_go_bankrupt(
                             deficit_still_not_paid, emergency_savings, accounts, investor)
                    #print """I didn't think hard about this case, since it's rare, so check back if I ever enter it. It's also bad tax-wise to rebalance, so try to avoid doing this."""
                    # It's bad to rebalance using equity because of 1. capital-gains tax 2. transactions costs 3. bid-ask spreads
                    # if this happens, no money left to 2. pay principal, 3. pay down margin if it's over limit, or 4. buy ETF
                else:
                    # 2. pay some principal, if we're dong that
                    number_of_pay_periods_until_donation_date = (days_from_start_to_donation_date - day) / INTEREST_AND_SALARY_EVERY_NUM_DAYS
                    amount_of_principal_to_repay = util.per_period_annuity_payment_of_principal(accounts["margin"].margin, number_of_pay_periods_until_donation_date,market.annual_margin_interest_rate, investor.pay_principal_throughout)
                    if amount_of_principal_to_repay > pay_after_interest:
                        accounts["margin"].margin -= pay_after_interest
                        deficit_still_not_paid = accounts["margin"].voluntary_rebalance(
                            day, taxes["margin"], years_remaining) # pay for the principal with equity
                        (emergency_savings, accounts, margin_strategy_went_bankrupt) = \
                             check_if_margin_strategy_should_use_emergency_funds_and_maybe_go_bankrupt(
                                 deficit_still_not_paid, emergency_savings, accounts, investor)
                        #print "WARNING: You're paying for principal with equity. This incurs tax costs and so should be minimized!"
                        # It's bad to rebalance using equity because of 1. capital-gains tax 2. transactions costs 3. bid-ask spreads
                    else:
                        accounts["margin"].margin -= amount_of_principal_to_repay
                        pay_after_interest_and_principal = pay_after_interest - amount_of_principal_to_repay
                        # 3. pay down margin if it's over limit
                        amount_to_pay_for_voluntary_margin_call = accounts["margin"].debt_to_pay_off_to_restore_voluntary_max_margin_to_assets_ratio(taxes["margin"], years_remaining)
                        if amount_to_pay_for_voluntary_margin_call > pay_after_interest_and_principal:
                            # pay what we can
                            accounts["margin"].margin -= pay_after_interest_and_principal
                            # use equity for the rest
                            deficit_still_not_paid = accounts["margin"].voluntary_rebalance(
                                day, taxes["margin"], years_remaining)
                            (emergency_savings, accounts, margin_strategy_went_bankrupt) = \
                                 check_if_margin_strategy_should_use_emergency_funds_and_maybe_go_bankrupt(
                                     deficit_still_not_paid, emergency_savings, accounts, investor)
                        else:
                            # just pay off voluntary margin call
                            accounts["margin"].margin -= amount_to_pay_for_voluntary_margin_call
                            pay_after_interest_and_principal_and_margincall = pay_after_interest_and_principal - amount_to_pay_for_voluntary_margin_call
                            # 4. buy some ETF
                            accounts["margin"].buy_ETF_at_fixed_ratio(pay_after_interest_and_principal_and_margincall, day, years_remaining)
            
            # If we're rebalancing upwards to increase leverage when it's too low, do that.
            if investor.rebalance_monthly_to_increase_leverage:
                accounts["margin"].voluntary_rebalance_to_increase_leverage(day, years_remaining)

            # Possibly get laid off or return to work
            num_times_randgenerator_was_called = investor.randomly_update_employment_status_this_month(
                randgenerator, num_times_randgenerator_was_called)
        
        if day % DAYS_PER_YEAR == TAX_DAY:
            for type in ["regular", "margin"]: # No "matched401k" because 401k accounts don't pay taxes!
                bill_or_refund = taxes[type].process_taxes()
                if type is "regular":
                    assert bill_or_refund == 0, "Regular strategy should never pay taxes because it never sells securities."
                if bill_or_refund > 0: # have to pay IRS bill
                    accounts[type].margin += bill_or_refund
                    deficit_still_not_paid = accounts[type].voluntary_rebalance(
                        day, taxes[type], years_remaining)
                    """The above operation to pay taxes by selling securities works
                    for any account type because for the non-margin accounts, the max
                    margin-to-assets ratio is zero, so the margin we add should be 
                    removed by rebalancing."""
                    if deficit_still_not_paid > 0:
                        print "WARNING: %s account is using %s of emergency funds to pay taxes. This is rare." % (type, util.format_as_dollar_string(deficit_still_not_paid))
                    """Note that capital-gains taxes alone shouldn't put you in debt for
                    a non-margin account. Why not? Say you had a net gain. Then you have enough
                    to pay the taxes. Say you had a net loss. Then you don't pay taxes. I suppose
                    you could have a net gain through Dec. 31 and then suffer a massive
                    loss before tax day the next year, but that's rare. If it happens, I'll find
                    out when this assertion is triggered.
                    Actually, I think the same reasoning applies to margin accounts: They
                    also shouldn't go into debt from capital-gains taxes."""
                    if type is not "margin":
                        assert deficit_still_not_paid == 0, "Non-margin accounts don't pay taxes much less dig into emergency fund to pay them."
                        assert accounts[type].margin < TINY_NUMBER, \
                            "Margin wasn't all eliminated from non-margin accounts. :("
                    else:
                        (emergency_savings, accounts, margin_strategy_went_bankrupt) = \
                                check_if_margin_strategy_should_use_emergency_funds_and_maybe_go_bankrupt(
                                    deficit_still_not_paid, emergency_savings, accounts, investor)
                elif bill_or_refund < 0: # got IRS refund
                    refund_as_positive_number = -bill_or_refund
                    if type is "margin":
                        if margin_strategy_gap_in_emergency_funds(emergency_savings) >= refund_as_positive_number:
                            emergency_savings["margin"] += refund_as_positive_number
                            refund_as_positive_number = 0
                        else:
                            refund_as_positive_number -= margin_strategy_gap_in_emergency_funds(emergency_savings)
                            emergency_savings["margin"] += margin_strategy_gap_in_emergency_funds(emergency_savings)
                            assert emergency_savings["margin"] == emergency_savings["regular"], \
                                "We didn't get margin's emergency savings back up to snuff."
                    assert refund_as_positive_number >= 0, "refund_as_positive_number somehow got negative!"
                    if refund_as_positive_number > 0: # might be set to 0 if type is "margin" and had to restore emergency savings
                        accounts[type].buy_ETF_at_fixed_ratio(refund_as_positive_number, day, years_remaining) # use the tax refund to buy more shares
                else:
                    pass

        if investor.do_tax_loss_harvesting and day % DAYS_PER_YEAR == TAX_LOSS_HARVEST_DAY:
            for type in ["regular", "margin"]: # No "matched401k" because its gains/losses aren't taxed!
                accounts[type].tax_loss_harvest(day, taxes[type])

        if day == days_from_start_to_donation_date-1 and iter_num in [1,10,100]:
            """Print out the market return and employment status on the last day. This helps
            see whether it's the same across different variants that I run. It should be
            when using random seed."""
            print "On day %i, the market returned %f, and investor_unemployed = %s" % \
                (day, random_daily_return, investor.laid_off)

        if PRINT_DEBUG_STUFF and iter_num == 1:
            print "Day %i, regular = %s, lev = %s, emerg_lev = %s" % (day, \
            util.format_as_dollar_string(simple_approx_account_values["regular"]), \
            util.format_as_dollar_string(simple_approx_account_values["margin"]), \
            util.format_as_dollar_string(emergency_savings["margin"]))

    # Make sure our variables are in order.
    have_assets_and_no_savings_gap = accounts["margin"].assets > 0 and margin_strategy_gap_in_emergency_funds(emergency_savings) == 0
    have_savings_gap_and_no_assets = accounts["margin"].assets == 0 and margin_strategy_gap_in_emergency_funds(emergency_savings) > 0
    have_no_assets_and_no_savings_gap = accounts["margin"].assets == 0 and margin_strategy_gap_in_emergency_funds(emergency_savings) == 0
    if have_no_assets_and_no_savings_gap:
        print "WARNING: You have no assets and no savings gap."
        assert have_assets_and_no_savings_gap or have_savings_gap_and_no_assets or have_no_assets_and_no_savings_gap, "Variables are messed up!"

    if accounts["margin"].assets > 0:
        """Now that we've donated, finish up. We need to pay off all margin debt. In
        the process of buying/selling, we incur capital-gains taxes (positive or negative).
        As a result of that, we need to sell/buy more. That may incur more taxes, necessitating
        repeating the cycle until convergence. We pretend it's tax day just to close out the
        tax issues, even though it's not actually tax day."""
        deficit_still_not_paid = accounts["margin"].pay_off_all_margin(
            days_from_start_to_donation_date, taxes["margin"])
        if not (deficit_still_not_paid > 0):
            bill_or_refund = taxes["margin"].process_taxes()
            while bill_or_refund > THRESHOLD_FOR_TAX_CONVERGENCE and not (deficit_still_not_paid > 0):
                accounts["margin"].margin += bill_or_refund
                deficit_still_not_paid = accounts["margin"].pay_off_all_margin(
                    days_from_start_to_donation_date, taxes["margin"])
                bill_or_refund = taxes["margin"].process_taxes()
            if bill_or_refund < 0 and not (deficit_still_not_paid > 0):
                accounts["margin"].buy_ETF_without_margin(-bill_or_refund, days_from_start_to_donation_date) # can't use margin anymore because we're done paying off loans
        assert accounts["margin"].margin == 0, "We haven't paid off all margin!"
    else:
        assert accounts["margin"].assets == 0, "If we have net self-debt, we shouldn't have assets."
    (emergency_savings, accounts, margin_strategy_went_bankrupt) = \
            check_if_margin_strategy_should_use_emergency_funds_and_maybe_go_bankrupt(
                deficit_still_not_paid, emergency_savings, accounts, investor)

    if accounts["regular"].assets_minus_margin() < TINY_NUMBER:
        print "WARNING: In this simulation round, the regular account ended with only %s." % \
            util.format_as_dollar_string(accounts["regular"].assets_minus_margin())

    for type in TYPES:
        assert accounts[type].margin == 0, "We shouldn't have any margin loans left. Regular and 401k accounts never had them, and margin accounts either paid them off or went bankrupt. But account type %s still has margin of %d. :(" % (type, accounts[type].margin)

    # Possibly save this trajectory of regular vs. margin wealth
    if iter_num < num_margin_trajectories_to_save_as_figures:
        plots.graph_margin_vs_regular_trajectories(historical_regular_wealth, \
            historical_margin_wealth, outfilepath, iter_num)

    # Return present values of the account balances
    real_present_value_function = lambda wealth: market.real_present_value(wealth,investor.years_until_donate)
    historical_margin_wealth = map(real_present_value_function, historical_margin_wealth)

    # Ending balances
    ending_balances = [accounts[type].assets_minus_margin() + emergency_savings[type] for type in TYPES]
    real_present_value_of_ending_balances = map(real_present_value_function,ending_balances)
    real_present_value_of_simple_calc_ending_margin_balance = \
        market.real_present_value(simple_approx_account_values["margin"] + \
        emergency_savings["margin"],investor.years_until_donate)

    return tuple(real_present_value_of_ending_balances) + (historical_margin_to_assets_ratios, \
        historical_margin_wealth, historical_carried_cap_gains, \
        historical_margin_percent_differences_from_simple_calc, have_savings_gap_and_no_assets, \
        margin_strategy_went_bankrupt, num_times_randgenerator_was_called, \
        real_present_value_of_simple_calc_ending_margin_balance, )

def margin_strategy_gap_in_emergency_funds(emergency_savings):
    return emergency_savings["regular"] - emergency_savings["margin"]

def check_if_margin_strategy_should_use_emergency_funds_and_maybe_go_bankrupt(
    deficit_still_not_paid, emergency_savings, accounts, investor):
    # Pay bills from emergency $, maybe go bankrupt if bills are too high.
    margin_strategy_went_bankrupt = False
    if deficit_still_not_paid > 0:
        if deficit_still_not_paid <= emergency_savings["margin"]:
            emergency_savings["margin"] -= deficit_still_not_paid
        else:
            amount_cannot_pay = deficit_still_not_paid - emergency_savings["margin"]
            emergency_savings["margin"] = 0 # pay what we can; the rest of our debt goes away with bankruptcy
            print "Margin strategy is going bankrupt with %s of unpaid debt." % \
                util.format_as_dollar_string(amount_cannot_pay)
            margin_strategy_went_bankrupt = True
            """Set margin account to have 0 as max margin-to-assets ratio because we're
            not using margin investing anymore (since our credit score, etc. is hammered)."""
            accounts["margin"] = BrokerageAccount.BrokerageAccount(0,0,0, \
                investor.taper_off_leverage_toward_end, \
                investor.initial_personal_max_margin_to_assets_relative_to_broker_max)
    return (emergency_savings, accounts, margin_strategy_went_bankrupt)

def run_samples(investor,market,num_samples,outfilepath,output_queue=None,
                verbosity=1,num_margin_trajectories_to_save_as_figures=10,
                use_seed_for_randomness=True):
    if use_seed_for_randomness:
        randgenerator = Random("seedy character")
    else:
        randgenerator = None
    account_values = dict()
    account_types = ["regular", "margin", "matched401k"]
    NUM_HISTORIES_TO_PLOT = 20
    PRINT_PROGRESS_AFTER_THESE_PERCENTS_DONE = sorted([.01, .1, .25, .5, .9])
    margin_to_assets_ratio_histories = []
    wealth_histories = []
    carried_cap_gains_histories = []
    margin_percent_differences_from_simple_calc_list = []
    running_average_margin_to_assets_ratios = None
    num_times_margin_ended_with_emergency_savings_gap = 0
    num_times_margin_strategy_went_bankrupt = 0
    prev_num_times_randgenerator_was_called = -9999 # junk
    running_sum_simple_calc_ending_balance = 0
    for type in account_types:
        account_values[type] = []
    num_margin_trajectories_to_save_as_figures = min(num_margin_trajectories_to_save_as_figures, 
                                                     num_samples) # save fewer figures if we don't have enough samples

    start_time = time.time()
    for sample in xrange(num_samples):
        (regular_val, margin_val, matched_401k_val, margin_to_assets_ratios, 
         margin_wealth, carried_cap_gains, margin_percent_differences_from_simple_calc, 
         margin_account_has_emergency_savings_gap,
         margin_strategy_went_bankrupt, num_times_randgenerator_was_called,
         simple_calc_ending_balance) = \
             one_run(investor,market,verbosity,outfilepath,sample, \
             num_margin_trajectories_to_save_as_figures,randgenerator)
        if sample > 0:
            assert prev_num_times_randgenerator_was_called == num_times_randgenerator_was_called, \
                "All iterations should call randgenerator equal numbers of times."
        prev_num_times_randgenerator_was_called = num_times_randgenerator_was_called

        """
        print "simple_calc_ending_balance = %s" % util.format_as_dollar_string(simple_calc_ending_balance)
        print "margin_val = %s" % util.format_as_dollar_string(margin_val)
        """

        account_values["regular"].append(regular_val)
        account_values["margin"].append(margin_val)
        account_values["matched401k"].append(matched_401k_val)

        if len(margin_to_assets_ratio_histories) < NUM_HISTORIES_TO_PLOT:
            margin_to_assets_ratio_histories.append(margin_to_assets_ratios)
        if len(wealth_histories) < NUM_HISTORIES_TO_PLOT:
            wealth_histories.append(margin_wealth)
        if len(carried_cap_gains_histories) < NUM_HISTORIES_TO_PLOT:
            carried_cap_gains_histories.append(carried_cap_gains)
        if len(margin_percent_differences_from_simple_calc_list) < NUM_PERCENT_DIFFS_TO_PLOT:
            margin_percent_differences_from_simple_calc_list.append(margin_percent_differences_from_simple_calc)
        running_sum_simple_calc_ending_balance += simple_calc_ending_balance
        if running_average_margin_to_assets_ratios is None:
            running_average_margin_to_assets_ratios = copy.copy(margin_to_assets_ratios)
        else:
            running_average_margin_to_assets_ratios += margin_to_assets_ratios
        if margin_account_has_emergency_savings_gap:
            num_times_margin_ended_with_emergency_savings_gap += 1
        if margin_strategy_went_bankrupt:
            num_times_margin_strategy_went_bankrupt += 1

        if verbosity > 0:
            NUM_SAMPLES_FOR_TIMING = 10
            if sample+1 == NUM_SAMPLES_FOR_TIMING:
                stop_time = time.time()
                samples_remaining_divided_by_samples_so_far = (num_samples-NUM_SAMPLES_FOR_TIMING)/NUM_SAMPLES_FOR_TIMING
                est_hours_to_complete_this_function = (stop_time-start_time)*samples_remaining_divided_by_samples_so_far/(60*60)
                print "Estimated hours to complete this round = %f" % est_hours_to_complete_this_function

            if PRINT_PROGRESS_AFTER_THESE_PERCENTS_DONE:
                iter_threshold_for_next_percent = PRINT_PROGRESS_AFTER_THESE_PERCENTS_DONE[0] * num_samples
                if sample >= iter_threshold_for_next_percent:
                    print "%s%% done  " % int(round(100.0 * sample/num_samples,0))
                    while PRINT_PROGRESS_AFTER_THESE_PERCENTS_DONE and PRINT_PROGRESS_AFTER_THESE_PERCENTS_DONE[0] * num_samples <= sample:
                        PRINT_PROGRESS_AFTER_THESE_PERCENTS_DONE.pop(0)
    print ""

    avg_margin_to_assets_ratios = running_average_margin_to_assets_ratios / num_samples

    numpy_regular = numpy.array(account_values["regular"])
    numpy_margin = numpy.array(account_values["margin"])
    if output_queue:
        (ratio_of_means, ratio_of_means_error) = util.ratio_of_means_with_error_bars(
            numpy_margin,numpy_regular)
        ratio_of_medians = numpy.median(numpy_margin)/numpy.median(numpy_regular)
        (ratio_of_exp_util, ratio_of_exp_util_error) = util.ratio_of_means_with_error_bars(
            map(math.sqrt, numpy_margin), 
            map(math.sqrt, numpy_regular))
        N_to_1_leverage = util.max_margin_to_assets_ratio_to_N_to_1_leverage(investor.broker_max_margin_to_assets_ratio)
        assert N_to_1_leverage >= 1, "N_to_1_leverage is < 1"
        output_queue.put( (N_to_1_leverage, ratio_of_means, ratio_of_means_error,
                           ratio_of_medians, ratio_of_exp_util, ratio_of_exp_util_error) )

    if outfilepath:
        with open(write_results.results_table_file_name(outfilepath), "w") as outfile:
            write_results.write_file_table(account_values, account_types, \
                float(num_times_margin_strategy_went_bankrupt)/num_samples, outfile, \
                fraction_times_margin_ended_with_emergency_savings_gap=float(num_times_margin_ended_with_emergency_savings_gap)/num_samples, \
                avg_simple_calc_value=running_sum_simple_calc_ending_balance/num_samples)
        with open(write_results.other_results_file_name(outfilepath), "w") as outfile:
            write_results.write_means(account_values, investor.years_until_donate, outfile)
            write_results.write_percentiles(account_values, outfile)
            write_results.write_winner_for_each_percentile(account_values, outfile)
        
        plots.graph_histograms(account_values, num_samples, outfilepath)
        plots.graph_expected_utility_vs_alpha(numpy_regular, numpy_margin, outfilepath)
        plots.graph_expected_utility_vs_wealth_saturation_cutoff(numpy_regular, numpy_margin, outfilepath, 4, 7)
        plots.graph_historical_margin_to_assets_ratios(margin_to_assets_ratio_histories, 
                                                       avg_margin_to_assets_ratios, outfilepath)
        plots.graph_historical_wealth_trajectories(wealth_histories, outfilepath)
        plots.graph_carried_cap_gains_trajectories(carried_cap_gains_histories, outfilepath)
        plots.graph_percent_differences_from_simple_calc(
            margin_percent_differences_from_simple_calc_list, outfilepath)
    
    print "randgenerator called %i times. Check that this is equal across variants!" % \
        num_times_randgenerator_was_called
    # TODO: return (mean_%_better, median%better)

def args_for_this_scenario(scenario_name, num_trials, outdir_name):
    """Give scenario name, return args to use for running it."""

    # Get default values
    default_investor = Investor.Investor()
    default_market = Market.Market()
    prefix = SCENARIOS[scenario_name]
    outpath = path.join(outdir_name, prefix)

    if scenario_name == "Default":
        return (default_investor,default_market,num_trials,outpath)
    if scenario_name == "Personal max margin is broker max":
        investor = Investor.Investor(initial_personal_max_margin_to_assets_relative_to_broker_max=1.0)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "No unemployment or inflation or taxes or black swans, only paid in first month, don't taper off leverage toward end, voluntary max leverage equals broker max leverage, no emergency savings":
        tax_rates = TaxRates.TaxRates(short_term_cap_gains_rate=0,
                                      long_term_cap_gains_rate=0,
                                      state_income_tax=0)
        investor = Investor.Investor(monthly_probability_of_layoff=0,
                                     tax_rates=tax_rates,
                                     do_tax_loss_harvesting=False,
                                     only_paid_in_first_month_of_sim=True,
                                     taper_off_leverage_toward_end=False,
                                     initial_personal_max_margin_to_assets_relative_to_broker_max=1.0,
                                     initial_emergency_savings=0)
        market = Market.Market(inflation_rate=0,medium_black_swan_prob=0,
                               large_black_swan_prob=0)
        return (investor,market,num_trials,outpath)
    elif scenario_name == "No unemployment or inflation or taxes or black swans, don't taper off leverage toward end, voluntary max leverage equals broker max leverage, no emergency savings":
        tax_rates = TaxRates.TaxRates(short_term_cap_gains_rate=0,
                                      long_term_cap_gains_rate=0,
                                      state_income_tax=0)
        investor = Investor.Investor(monthly_probability_of_layoff=0,
                                     tax_rates=tax_rates,
                                     do_tax_loss_harvesting=False,
                                     taper_off_leverage_toward_end=False,
                                     initial_personal_max_margin_to_assets_relative_to_broker_max=1.0,
                                     initial_emergency_savings=0)
        market = Market.Market(inflation_rate=0,medium_black_swan_prob=0,
                               large_black_swan_prob=0)
        return (investor,market,num_trials,outpath)
    elif scenario_name == "No unemployment or inflation or taxes or black swans, don't taper off leverage toward end, no emergency savings":
        tax_rates = TaxRates.TaxRates(short_term_cap_gains_rate=0,
                                      long_term_cap_gains_rate=0,
                                      state_income_tax=0)
        investor = Investor.Investor(monthly_probability_of_layoff=0,
                                     tax_rates=tax_rates,
                                     do_tax_loss_harvesting=False,
                                     taper_off_leverage_toward_end=False,
                                     initial_emergency_savings=0)
        market = Market.Market(inflation_rate=0,medium_black_swan_prob=0,
                               large_black_swan_prob=0)
        return (investor,market,num_trials,outpath)
    elif scenario_name == "No unemployment or inflation or taxes or black swans, no emergency savings":
        tax_rates = TaxRates.TaxRates(short_term_cap_gains_rate=0,
                                      long_term_cap_gains_rate=0,
                                      state_income_tax=0)
        investor = Investor.Investor(monthly_probability_of_layoff=0,
                                     tax_rates=tax_rates,
                                     do_tax_loss_harvesting=False,
                                     initial_emergency_savings=0)
        market = Market.Market(inflation_rate=0,medium_black_swan_prob=0,
                               large_black_swan_prob=0)
        return (investor,market,num_trials,outpath)
    elif scenario_name == "No unemployment or inflation or taxes, no emergency savings":
        tax_rates = TaxRates.TaxRates(short_term_cap_gains_rate=0,
                                      long_term_cap_gains_rate=0,
                                      state_income_tax=0)
        investor = Investor.Investor(monthly_probability_of_layoff=0,
                                     tax_rates=tax_rates,
                                     do_tax_loss_harvesting=False,
                                     initial_emergency_savings=0)
        market = Market.Market(inflation_rate=0)
        return (investor,market,num_trials,outpath)
    elif scenario_name == "No unemployment or inflation, no emergency savings":
        investor = Investor.Investor(monthly_probability_of_layoff=0,
                                     initial_emergency_savings=0)
        market = Market.Market(inflation_rate=0)
        return (investor,market,num_trials,outpath)
    elif scenario_name == "No unemployment, no emergency savings":
        investor = Investor.Investor(monthly_probability_of_layoff=0,
                                     initial_emergency_savings=0)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "No emergency savings":
        investor = Investor.Investor(initial_emergency_savings=0)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "Emergency savings = $1 million":
        investor = Investor.Investor(initial_emergency_savings=1000000)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "Don't rebalance monthly":
        investor = Investor.Investor(rebalance_monthly_to_increase_leverage=False)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "Favored tax ordering when liquidate":
        investor = Investor.Investor(does_broker_liquidation_sell_tax_favored_first=True)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "Use VIX data":
        market = Market.Market(use_VIX_data_for_volatility=True)
        return (default_investor,market,num_trials,outpath)
    elif scenario_name == "Pay down principal throughout investment period":
        investor = Investor.Investor(rebalance_monthly_to_increase_leverage=False,pay_principal_throughout=True)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "Annual sigma = .4":
        market = Market.Market(annual_sigma=.4)
        return (default_investor,market,num_trials,outpath)
    elif scenario_name == "Annual sigma = 0":
        market = Market.Market(annual_sigma=0,medium_black_swan_prob=0,
                               large_black_swan_prob=0)
        investor = Investor.Investor(monthly_probability_of_layoff=0)
        return (investor,market,num_trials,outpath)
    elif scenario_name == "Annual mu = .1":
        market = Market.Market(annual_mu=.1)
        return (default_investor,market,num_trials,outpath)
    elif scenario_name == "Annual mu = .1, don't rebalance monthly":
        investor = Investor.Investor(rebalance_monthly_to_increase_leverage=False)
        market = Market.Market(annual_mu=.1)
        return (investor,market,num_trials,outpath)
    elif scenario_name == "Annual mu = .07":
        market = Market.Market(annual_mu=.07)
        return (default_investor,market,num_trials,outpath)
    elif scenario_name == "Annual mu = .04":
        market = Market.Market(annual_mu=.04)
        return (default_investor,market,num_trials,outpath)
    elif scenario_name == "Annual mu = -.02":
        market = Market.Market(annual_mu=-.02)
        return (default_investor,market,num_trials,outpath)
    elif scenario_name == "Annual margin interest rate = .015":
        market = Market.Market(annual_margin_interest_rate=.015)
        return (default_investor,market,num_trials,outpath)
    elif scenario_name == "Donate after 5 years":
        investor = Investor.Investor(years_until_donate=5)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "Donate after 30 years":
        investor = Investor.Investor(years_until_donate=30)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "Don't taper off leverage toward end":
        investor = Investor.Investor(taper_off_leverage_toward_end=False)
        return (investor,default_market,num_trials,outpath)
    elif scenario_name == "Don't rebalance monthly and don't taper off leverage toward end":
        investor = Investor.Investor(rebalance_monthly_to_increase_leverage=False,
                                     taper_off_leverage_toward_end=False)
        return (investor,default_market,num_trials,outpath)
    else:
        raise Exception(scenario_name + " is not a known scenario type.")

def sweep_scenarios(approx_num_simultaneous_processes, num_trials):
    """Sweep all the scenarios! (http://knowyourmeme.com/memes/x-all-the-y)"""
    outdir_name = util.create_timestamped_dir("swp") # concise way of writing "sweep scenarios"

    # Scenarios
    scenarios_to_run = SCENARIOS.keys()

    # Run scenarios
    processes = []
    process_num = 1
    for scenario in scenarios_to_run:
        print "\n\n" + scenario
        p = Process(target=run_samples,
                    args=args_for_this_scenario(scenario,num_trials,outdir_name))
        p.start()
        if enough_processes_running(process_num,approx_num_simultaneous_processes):
            p.join()
        processes.append(p)
        process_num += 1

    # Wait for all processes to finish
    for process in processes:
        process.join()

def enough_processes_running(process_num, approx_num_simultaneous_processes):
    """This is a hacky method to control the number of processes. The actual
    number of simultaneous processes can be anywhere from 1 to
    2 * approx_num_simultaneous_processes - 1. For example, if
    approx_num_simultaneous_processes == 3, then we run the first
    3 processes. If the third one finishes last, we wait for it, and while
    it's running, there's just 1 process. If the third one finishes first,
    we let another 3 processes go before joining again, so there are 5
    running at that point."""
    return process_num % approx_num_simultaneous_processes == 0

def dir_prefix_for_optimal_leverage_specific_scenario(scenario_name):
    # sclev is short for "scenario-specific optimal leverage graph"
    return "sclev_{}".format(SCENARIOS[scenario_name])

def file_prefix_for_optimal_leverage_specific_scenario(max_margin_to_assets):
    max_margin_to_assets_without_decimal = int(round(max_margin_to_assets * 100,0))
    return "MaxMTApct{}".format(max_margin_to_assets_without_decimal)

def get_performance_vs_leverage_amount_by_scenario(scenario_name, num_trials, 
                                                   use_timestamped_dirs, cur_working_dir, 
                                                   approx_num_simultaneous_processes,
                                                   leverage_amounts_to_try=[1.0,1.5,2.0,2.5,3.0,4.0]):
    print "\n\n==Getting optimal leverage for scenario = {}==".format(scenario_name)

    output_queue = Queue() # multiprocessing queue

    dir_prefix = dir_prefix_for_optimal_leverage_specific_scenario(scenario_name)
    dir = path.join(cur_working_dir, dir_prefix)
    if use_timestamped_dirs:
        outdir_name = util.create_timestamped_dir(dir)
    else:
        outdir_name = dir
        os.mkdir(outdir_name) # let it fail if already exists
    
    """
    ONLY USE THIS IF CALCULATING WHICH LEVERAGE VALUES TO TRY BASED ON A RANGE AND STEP SIZE:
    assert range_stop >= range_start, "Stopping range value must be at least as big as starting range value."
    num_steps = int((range_stop-range_start)/step_size)+1
    """
    processes = []
    process_num = 1
    #for N_to_1_leverage in numpy.linspace(range_start, range_stop, num_steps):
    for N_to_1_leverage in leverage_amounts_to_try:
        max_margin_to_assets = util.N_to_1_leverage_to_max_margin_to_assets_ratio(N_to_1_leverage)
        print "\n\n\nMax margin-to-assets ratio = ", max_margin_to_assets
        args = args_for_this_scenario(scenario_name, num_trials, outdir_name)

        # Change broker_max_margin_to_assets_ratio from default configuration
        investor = args[0]
        investor.broker_max_margin_to_assets_ratio = max_margin_to_assets
        market = args[1]

        outpath = path.join(outdir_name, file_prefix_for_optimal_leverage_specific_scenario(max_margin_to_assets))
        p = Process(target=run_samples, 
                args=(investor,market,num_trials,outpath,output_queue))
        p.start()
        if enough_processes_running(process_num,approx_num_simultaneous_processes):
            p.join()
        processes.append(p)
        process_num += 1
    
    # Wait for all processes to finish
    for process in processes:
        process.join()

    # Once they're done, plot them
    plots.graph_trends_vs_leverage_amount(output_queue, outdir_name)

def optimal_leverage_for_all_scenarios(num_trials, use_timestamped_dirs, cur_working_dir,
                                       approx_num_simultaneous_processes):
    """Get graphs of optimal leverage over all scenarios. This may take days/weeks to 
    finish running!"""
    scenarios_not_to_sweep = ["closetotheoryminus%i" % i for i in [2,3,4,5,6]]
    scenarios_not_to_sweep.append("sig0")
    scenarios_not_to_sweep.append("persmaxbrokermax")
    scenarios_not_to_sweep.append("default")# comment out later
    scenarios_not_to_sweep.append("closetotheory")# comment out later
    scenarios_not_to_sweep.append("closetotheoryminus7")# comment out later
    scenarios_not_to_sweep.append("emergsav1m")# comment out later
    for scenario_name in SCENARIOS.keys():
        if SCENARIOS[scenario_name] in scenarios_not_to_sweep: # skip them to speed up computing
            """In this case, only get results for the default margin-to-assets setting
            because we don't actually care about sensitivity analysis here."""
            default_investor = Investor.Investor()
            default_leverage = util.max_margin_to_assets_ratio_to_N_to_1_leverage(default_investor.broker_max_margin_to_assets_ratio)
            get_performance_vs_leverage_amount_by_scenario(scenario_name,num_trials,
                                                           use_timestamped_dirs,cur_working_dir,
                                                           approx_num_simultaneous_processes,
                                                           leverage_amounts_to_try=[default_leverage])
        else:
            """Use default range for the param sweep."""
            get_performance_vs_leverage_amount_by_scenario(scenario_name,num_trials,
                                                           use_timestamped_dirs,cur_working_dir,
                                                           approx_num_simultaneous_processes)

def run_one_variant(num_trials):
    outdir_name = util.create_timestamped_dir("one") # concise way of writing "one variant"
    #scenario = "Default"
    scenario = "Personal max margin is broker max"
    #scenario = "No unemployment or inflation or taxes or black swans, only paid in first month, don't taper off leverage toward end, voluntary max leverage equals broker max leverage, no emergency savings"
    #scenario = "No unemployment or inflation or taxes or black swans, don't taper off leverage toward end, no emergency savings"
    args = args_for_this_scenario(scenario, num_trials, outdir_name)
    run_samples(*args)

if __name__ == "__main__":
    #sweep_scenarios(1,1)
    run_one_variant(1)
"""
Things that need to be checked because I sometimes set them to run faster:
- years (15 vs. .1)
- SCENARIOS at top of this file
- scenarios_not_to_sweep may have "default" or "closetotheory"
- num trials for margin
- num trials for lev ETFs
Also check
- num processes
- LOCAL_FILE_PATHS_IN_HTML
- using seed
"""