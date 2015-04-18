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
from multiprocessing import Process, Queue

DAYS_PER_YEAR = 365
SATURDAY = 6
SUNDAY = 0
TAX_LOSS_HARVEST_DAY = 360 # day number 360 in late Dec
TAX_DAY = 60 # day of tax payments/refund assuming you get your refund around March 1; ignoring payments during the year...
TINY_NUMBER = .000001
THRESHOLD_FOR_TAX_CONVERGENCE = 50

def one_run(investor,market,verbosity):
    days_from_start_to_donation_date = int(DAYS_PER_YEAR * investor.years_until_donate)
    accounts = dict()
    accounts["regular"] = BrokerageAccount.BrokerageAccount(0,0,0)
    accounts["margin"] = BrokerageAccount.BrokerageAccount(0,0,investor.broker_max_margin_to_assets_ratio)
    accounts["matched401k"] = BrokerageAccount.BrokerageAccount(0,0,0)
    taxes = dict()
    for type in ["regular", "margin", "matched401k"]:
        taxes[type] = Taxes.Taxes(investor.tax_rates)
    interest_and_salary_every_num_days = 30
    interest_and_salary_every_fraction_of_year = float(interest_and_salary_every_num_days) / DAYS_PER_YEAR

    # Record history over lifetime of investment
    historical_margin_to_assets_ratios = numpy.zeros(days_from_start_to_donation_date)
    historical_margin_wealth = numpy.zeros(days_from_start_to_donation_date)
    historical_carried_taxes = numpy.zeros(days_from_start_to_donation_date)

    for day in range(days_from_start_to_donation_date):
        # Record historical info for future reference
        historical_margin_to_assets_ratios[day] = accounts["margin"].margin_to_assets(taxes["margin"])
        historical_margin_wealth[day] = accounts["margin"].assets
        historical_carried_taxes[day] = taxes["margin"].total_gain_or_loss()

        # Stock market changes on weekdays
        if (day % 7 != SATURDAY) and (day % 7 != SUNDAY):
            random_daily_return = market.random_daily_return(day)

            accounts["regular"].update_asset_prices(random_daily_return)

            if not investor.margin_account_bankrupt:
                accounts["margin"].update_asset_prices(random_daily_return)
                investor.margin_account_bankrupt = accounts["margin"].mandatory_rebalance(
                    day, taxes["margin"], investor.does_broker_liquidation_sell_tax_favored_first)
                """Interactive Brokers (IB) forces you to stay within the mandated
                margin-to-assets ratio, (I think) on a day-by-day basis. The above
                function call simulates IB selling any positions
                as needed to restore the margin-to-assets ratio. Because IB
                is so strict about staying within the limits, the margin investor
                in this simulation voluntarily maintains a max margin-to-assets
                ratio somewhat below the broker-imposed limit."""

            accounts["matched401k"].update_asset_prices(random_daily_return)

        # check if we should get paid and defray interest
        if day % interest_and_salary_every_num_days == 0:
            years_elapsed = day/DAYS_PER_YEAR
            pay = investor.current_annual_income(years_elapsed, market.inflation_rate) * (float(interest_and_salary_every_num_days) / DAYS_PER_YEAR)
            
            if verbosity > 1:
                if day % 1000 == 0:
                    print "Day " + str(day) + ", year " + str(years_elapsed) ,

            # regular account just buys ETF
            accounts["regular"].buy_ETF_at_fixed_ratio(pay, day)

            # matched 401k account buys ETF with employee and employer funds
            accounts["matched401k"].buy_ETF_at_fixed_ratio(pay * (1+investor.match_percent_from_401k/100.0), day)

            if not investor.margin_account_bankrupt:
                # The next steps are for the margin account. It
                # 1. pays interest
                # 2. pays some principal on loans
                # 3. pay down margin if it's over limit
                # 4. buys new ETF with the remaining $

                # 1. pay interest
                interest = accounts["margin"].compute_interest(market.annual_margin_interest_rate,interest_and_salary_every_fraction_of_year)
                pay_after_interest = pay - interest
                if pay_after_interest <= 0:
                    accounts["margin"].margin += (interest - pay) # amount of interest remaining
                    investor.margin_account_bankrupt = accounts["margin"].voluntary_rebalance(
                        day, taxes["margin"]) # pay for the interest with equity
                    #print """I didn't think hard about this case, since it's rare, so check back if I ever enter it. It's also bad tax-wise to rebalance, so try to avoid doing this."""
                    # It's bad to rebalance using equity because of 1. capital-gains tax 2. transactions costs 3. bid-ask spreads
                    # if this happens, no money left to 2. pay principal, 3. pay down margin if it's over limit, or 4. buy ETF
                else:
                    # 2. pay some principal, if we're dong that
                    number_of_pay_periods_until_donation_date = (days_from_start_to_donation_date - day) / interest_and_salary_every_num_days
                    amount_of_principal_to_repay = util.per_period_annuity_payment_of_principal(accounts["margin"].margin, number_of_pay_periods_until_donation_date,market.annual_margin_interest_rate, investor.pay_principal_throughout)
                    if amount_of_principal_to_repay > pay_after_interest:
                        accounts["margin"].margin -= pay_after_interest
                        investor.margin_account_bankrupt = accounts["margin"].voluntary_rebalance(day, taxes["margin"]) # pay for the principal with equity
                        #print "WARNING: You're paying for principal with equity. This incurs tax costs and so should be minimized!"
                        # It's bad to rebalance using equity because of 1. capital-gains tax 2. transactions costs 3. bid-ask spreads
                    else:
                        accounts["margin"].margin -= amount_of_principal_to_repay
                        pay_after_interest_and_principal = pay_after_interest - amount_of_principal_to_repay
                        # 3. pay down margin if it's over limit
                        amount_to_pay_for_margin_call = accounts["margin"].debt_to_pay_off_to_restore_voluntary_max_margin_to_assets_ratio(taxes["margin"])
                        if amount_to_pay_for_margin_call > pay_after_interest_and_principal:
                            # pay what we can
                            accounts["margin"].margin -= pay_after_interest_and_principal
                            # use equity for the rest
                            investor.margin_account_bankrupt = accounts["margin"].voluntary_rebalance(day, taxes["margin"])
                        else:
                            # just pay off margin call
                            accounts["margin"].margin -= amount_to_pay_for_margin_call
                            pay_after_interest_and_principal_and_margincall = pay_after_interest_and_principal - amount_to_pay_for_margin_call
                            # 4. buy some ETF
                            accounts["margin"].buy_ETF_at_fixed_ratio(pay_after_interest_and_principal_and_margincall, day)
            
            # If we're rebalancing upwards to increase leverage when it's too low, do that.
            if investor.rebalance_monthly_to_increase_leverage and not investor.margin_account_bankrupt:
                accounts["margin"].rebalance_to_increase_leverage(day, taxes["margin"])

            # Possibly get laid off or return to work
            investor.randomly_update_employment_status_this_month()
        
        if day % DAYS_PER_YEAR == TAX_DAY:
            for type in ["regular", "margin", "matched401k"]:
                if type is not "margin" or not investor.margin_account_bankrupt:
                    bill_or_refund = taxes[type].process_taxes()
                    if bill_or_refund > 0: # have to pay IRS bill
                        accounts[type].margin += bill_or_refund
                        did_we_go_bankrupt = accounts[type].voluntary_rebalance(day, taxes[type])
                        """The above operation to pay taxes by selling securities works
                        for any account type because for the non-margin accounts, the max
                        margin-to-assets ratio is zero, so the margin we add should be 
                        removed by rebalancing. To confirm that, I add the following assertion."""
                        if type is not "margin":
                            assert accounts[type].margin < TINY_NUMBER, "Margin wasn't all eliminated from non-margin accounts. :("
                        else:
                            investor.margin_account_bankrupt = did_we_go_bankrupt
                            """We only keep track of whether the margin account is
                            bankrupt because the other types can't go bankrupt"""
                    elif bill_or_refund < 0: # got IRS refund
                        accounts[type].buy_ETF_at_fixed_ratio(-bill_or_refund, day) # use the tax refund to buy more shares
                    else:
                        pass

        if investor.do_tax_loss_harvesting and day % DAYS_PER_YEAR == TAX_LOSS_HARVEST_DAY:
            for type in ["regular", "margin", "matched401k"]:
                if type is not "margin" or not investor.margin_account_bankrupt:
                    accounts[type].tax_loss_harvest(day, taxes[type])

    if not investor.margin_account_bankrupt:
        """Now that we've donated, finish up. We need to pay off all margin debt. In
        the process of buying/selling, we incur capital-gains taxes (positive or negative).
        As a result of that, we need to sell/buy more. That may incur more taxes, necessitating
        repeating the cycle until convergence. We pretend it's tax day just to close out the
        tax issues, even though it's not actually tax day."""
        investor.margin_account_bankrupt = accounts["margin"].pay_off_all_margin(days_from_start_to_donation_date, taxes["margin"])
        if not investor.margin_account_bankrupt:
            bill_or_refund = taxes["margin"].process_taxes()
            while bill_or_refund > THRESHOLD_FOR_TAX_CONVERGENCE and not investor.margin_account_bankrupt:
                accounts["margin"].margin += bill_or_refund
                investor.margin_account_bankrupt = accounts["margin"].pay_off_all_margin(days_from_start_to_donation_date, taxes["margin"])
                bill_or_refund = taxes["margin"].process_taxes()
            if bill_or_refund < 0 and not investor.margin_account_bankrupt:
                accounts["margin"].buy_ETF_without_margin(-bill_or_refund, days_from_start_to_donation_date) # can't use margin anymore because we're done paying off loans

    if accounts["regular"].assets < TINY_NUMBER:
        print "WARNING: In this simulation round, the regular account ended with only ${}.".format(accounts["regular"].assets)

    # Return present values of the account balances
    historical_margin_wealth = map(lambda wealth: market.real_present_value(wealth,investor.years_until_donate), historical_margin_wealth)
    return (market.real_present_value(accounts["regular"].assets,investor.years_until_donate),
            market.real_present_value(accounts["margin"].assets,investor.years_until_donate),
            market.real_present_value(accounts["matched401k"].assets,investor.years_until_donate),
            historical_margin_to_assets_ratios, historical_margin_wealth, 
            historical_carried_taxes, investor.margin_account_bankrupt)

def run_samples(investor,market,num_samples=1000,outfilepath=None,output_queue=None,verbosity=1):
    account_values = dict()
    account_types = ["regular", "margin", "matched401k"]
    NUM_HISTORIES_TO_PLOT = 20
    PRINT_PROGRESS_EVERY_ITERATIONS = 10
    margin_to_assets_ratio_histories = []
    wealth_histories = []
    carried_tax_histories = []
    running_average_margin_to_assets_ratios = None
    num_margin_bankruptcies = 0
    for type in account_types:
        account_values[type] = []
    for sample in range(num_samples):
        (regular_val, margin_val, matched_401k_val, margin_to_assets_ratios, 
         margin_wealth, carried_taxes, margin_account_bankrupt) = one_run(
             investor,market,verbosity)
        account_values["regular"].append(regular_val)
        account_values["margin"].append(margin_val)
        account_values["matched401k"].append(matched_401k_val)

        if len(margin_to_assets_ratio_histories) < NUM_HISTORIES_TO_PLOT:
            margin_to_assets_ratio_histories.append(margin_to_assets_ratios)
        if len(wealth_histories) < NUM_HISTORIES_TO_PLOT:
            wealth_histories.append(margin_wealth)
        if len(carried_tax_histories) < NUM_HISTORIES_TO_PLOT:
            carried_tax_histories.append(carried_taxes)
        if running_average_margin_to_assets_ratios is None:
            running_average_margin_to_assets_ratios = copy.copy(margin_to_assets_ratios)
        else:
            running_average_margin_to_assets_ratios += margin_to_assets_ratios
        if margin_account_bankrupt:
            num_margin_bankruptcies += 1

        if verbosity > 0:
            if sample % PRINT_PROGRESS_EVERY_ITERATIONS == 0:
                print "Finished sample " + str(sample)

    avg_margin_to_assets_ratios = running_average_margin_to_assets_ratios / num_samples

    if output_queue:
        numpy_regular = numpy.array(account_values["regular"])
        numpy_margin = numpy.array(account_values["margin"])
        (ratio_of_means, ratio_of_means_error) = util.ratio_of_means_with_error_bars(numpy_margin,numpy_regular)
        ratio_of_medians = numpy.median(numpy_margin)/numpy.median(numpy_regular)
        (ratio_of_exp_util, ratio_of_exp_util_error) = util.ratio_of_means_with_error_bars(
            map(math.sqrt, numpy_margin), map(math.sqrt, numpy_regular))
        N_to_1_leverage = util.max_margin_to_assets_ratio_to_N_to_1_leverage(investor.broker_max_margin_to_assets_ratio)
        assert N_to_1_leverage >= 1, "N_to_1_leverage is < 1"
        output_queue.put( (N_to_1_leverage, ratio_of_means, ratio_of_means_error,
                           ratio_of_medians, ratio_of_exp_util, ratio_of_exp_util_error) )

    if outfilepath:
        with open(outfilepath + ".txt", "w") as outfile:
            write_results.write_file_table(account_values, account_types, float(num_margin_bankruptcies)/num_samples, outfile)
            outfile.write("\n")
            write_results.write_means(account_values, investor.years_until_donate, outfile)
            write_results.write_percentiles(account_values, outfile)
            write_results.write_winner_for_each_percentile(account_values, outfile)
        
        plots.graph_results(account_values, num_samples, outfilepath)
        plots.graph_historical_margin_to_assets_ratios(margin_to_assets_ratio_histories, avg_margin_to_assets_ratios, outfilepath)
        plots.graph_historical_wealth_trajectories(wealth_histories, outfilepath)
        plots.graph_carried_taxes_trajectories(carried_tax_histories, outfilepath)
    
    # TODO: return (mean_%_better, median%better)

def args_for_this_scenario(scenario_name, num_trials, outdir_name):
    """Give scenario name, return args to use for running it."""

    # Get default values
    default_investor = Investor.Investor()
    default_market = Market.Market()

    if scenario_name == "Default":
        return (default_investor,default_market,num_trials,outdir_name + "\default")
    elif scenario_name == "No unemployment or inflation":
        investor = Investor.Investor(monthly_probability_of_layoff=0,
                                     do_tax_loss_harvesting=False)
        market = Market.Market(inflation_rate=0)
        return (investor,market,num_trials,outdir_name + "\uit")
    elif scenario_name == "Rebalance to increase leverage":
        investor = Investor.Investor(rebalance_monthly_to_increase_leverage=True)
        return (investor,default_market,num_trials,outdir_name + "\inclev")
    elif scenario_name == "Rebalance to increase leverage, favored tax ordering when liquidate":
        investor = Investor.Investor(rebalance_monthly_to_increase_leverage=True,
                                     does_broker_liquidation_sell_tax_favored_first=True)
        return (investor,default_market,num_trials,outdir_name + "\inclevFO")
    elif scenario_name == "Rebalance to increase leverage, no tax-loss harvesting":
        investor = Investor.Investor(rebalance_monthly_to_increase_leverage=True,
                                     do_tax_loss_harvesting=False)
        return (investor,default_market,num_trials,outdir_name + "\inclevNH")
    elif scenario_name == "Use VIX data":
        market = Market.Market(use_VIX_data_for_volatility=True)
        return (default_investor,market,num_trials,outdir_name + "\VIX")
    elif scenario_name == "Pay down principal throughout investment period":
        investor = Investor.Investor(pay_principal_throughout=True)
        return (investor,default_market,num_trials,outdir_name + "\princthru")
    elif scenario_name == "Annual sigma = .4":
        market = Market.Market(annual_sigma=.4)
        return (default_investor,market,num_trials,outdir_name + "\sig4")
    elif scenario_name == "Annual sigma = 0":
        market = Market.Market(annual_sigma=0,medium_black_swan_prob=0,
                               large_black_swan_prob=0)
        investor = Investor.Investor(monthly_probability_of_layoff=0)
        return (investor,market,num_trials,outdir_name + "\novar")
    elif scenario_name == "Annual mu = .07":
        market = Market.Market(annual_mu=.07)
        return (default_investor,market,num_trials,outdir_name + "\mu07")
    elif scenario_name == "Annual margin interest rate = .015":
        market = Market.Market(annual_margin_interest_rate=.015)
        return (default_investor,market,num_trials,outdir_name + "\int_r015")
    elif scenario_name == "Donate after 10 years":
        investor = Investor.Investor(years_until_donate=10)
        return (investor,default_market,num_trials,outdir_name + "\yrs10")
    else:
        raise Exception(scenario_name + " is not a known scenario type.")

def sweep_scenarios(use_multiprocessing, quick_test=True):
    if quick_test:
        NUM_TRIALS = 2
    else:
        NUM_TRIALS = 1000

    outdir_name = util.create_timestamped_dir("swp") # concise way of writing "sweep scenarios"

    # Scenarios
    scenarios_to_run = ["No unemployment or inflation", 
                        "Rebalance to increase leverage, favored tax ordering when liquidate", 
                        "Rebalance to increase leverage, no tax-loss harvesting", 
                        "Annual sigma = 0",
                        "Rebalance to increase leverage", 
                        "Default", "Use VIX data", 
                        "Pay down principal throughout investment period", 
                        "Annual sigma = .4", "Annual mu = .07", 
                        "Annual margin interest rate = .015", 
                        "Donate after 10 years"]

    # Run scenarios
    processes = []
    for scenario in scenarios_to_run:
        print "\n\n" + scenario
        p = Process(target=run_samples,
                    args=args_for_this_scenario(scenario,NUM_TRIALS,outdir_name))
        p.start()
        if not use_multiprocessing:
            p.join()
        processes.append(p)

    # Wait for all processes to finish
    for process in processes:
        process.join()

def get_performance_vs_leverage_amount(use_multiprocessing, quick_test=True):
    if quick_test:
        NUM_TRIALS = 4
    else:
        NUM_TRIALS = 1000

    output_queue = Queue() # multiprocessing queue
    outdir_name = util.create_timestamped_dir("lev") # concise way of writing "test leverage amounts"
    
    RANGE_START = 1.0
    RANGE_STOP = 4.0
    STEP_SIZE = .25
    num_steps = int((RANGE_STOP-RANGE_START)/STEP_SIZE)+1
    processes = []
    for N_to_1_leverage in numpy.linspace(RANGE_START, RANGE_STOP, num_steps):
        max_margin_to_assets = util.N_to_1_leverage_to_max_margin_to_assets_ratio(N_to_1_leverage)
        print "\n\n\nRebalance to increase leverage, max margin-to-assets ratio = ", max_margin_to_assets
        #investor = Investor.Investor(rebalance_monthly_to_increase_leverage=True, broker_max_margin_to_assets_ratio=max_margin_to_assets)
        investor = Investor.Investor(broker_max_margin_to_assets_ratio=max_margin_to_assets)
        market = Market.Market()
        max_margin_to_assets_without_decimal = int(max_margin_to_assets * 100)
        p = Process(target=run_samples, 
                args=(investor,market,NUM_TRIALS,
                      outdir_name + "\inclev{}".format(max_margin_to_assets_without_decimal),
                      output_queue))
        p.start()
        if not use_multiprocessing:
            p.join()
        processes.append(p)
    
    # Wait for all processes to finish
    for process in processes:
        process.join()

    # Once they're done, plot them
    plots.graph_trends_vs_leverage_amount(output_queue, outdir_name)

def run_one_variant():
    outdir_name = util.create_timestamped_dir("one") # concise way of writing "one variant"
    num_trials = 2
    #scenario = "Rebalance to increase leverage"
    scenario = "Default"
    #scenario = "Rebalance to increase leverage, no tax-loss harvesting"
    args = args_for_this_scenario(scenario, num_trials, outdir_name)
    run_samples(*args)

if __name__ == "__main__":
    #sweep_scenarios(True,quick_test=False)
    get_performance_vs_leverage_amount(True,quick_test=False)
    #run_one_variant()