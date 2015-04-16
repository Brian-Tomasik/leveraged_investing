import util
import plots
import print_and_write
import Investor
import Market
import BrokerageAccount
import TaxRates
import numpy
import copy

# TODO: if lots of trading happens, consider counting trading fees

DAYS_PER_YEAR = 365
SATURDAY = 6
SUNDAY = 0
TINY_NUMBER = .000001

def one_run(investor,market,verbosity):
    days_from_start_to_donation_date = int(DAYS_PER_YEAR * investor.years_until_donate)
    regular_account = BrokerageAccount.BrokerageAccount(0,0,0)
    margin_account = BrokerageAccount.BrokerageAccount(0,0,investor.broker_max_margin_to_assets_ratio)
    matched_401k_account = BrokerageAccount.BrokerageAccount(0,0,0)
    interest_and_salary_every_num_days = 30
    interest_and_salary_every_fraction_of_year = float(interest_and_salary_every_num_days) / DAYS_PER_YEAR

    # Record history over lifetime of investment
    historical_margin_to_assets_ratios = numpy.zeros(days_from_start_to_donation_date)
    historical_margin_wealth = numpy.zeros(days_from_start_to_donation_date)

    for day in range(days_from_start_to_donation_date):
        # Record historical margin-to-assets ratio for future reference
        historical_margin_to_assets_ratios[day] = margin_account.margin_to_assets()
        historical_margin_wealth[day] = margin_account.assets

        # Stock market changes on weekdays
        if (day % 7 != SATURDAY) and (day % 7 != SUNDAY):
            random_daily_return = market.random_daily_return(day)

            regular_account.update_asset_prices(random_daily_return)

            margin_account.update_asset_prices(random_daily_return)
            margin_account.mandatory_rebalance(day, investor.tax_rates)
            """Interactive Brokers (IB) forces you to stay within the mandated
            margin-to-assets ratio, probably on a day-by-day basis. The above
            function call simulates IB selling any positions
            as needed to restore the margin-to-assets ratio. Because IB
            is so strict about staying within the limits, the margin investor
            in this simulation voluntarily maintains a max margin-to-assets
            ratio somewhat below the broker-imposed limit."""

            matched_401k_account.update_asset_prices(random_daily_return)

        # check if we should get paid and defray interest
        if day % interest_and_salary_every_num_days == 0:
            years_elapsed = day/DAYS_PER_YEAR
            pay = investor.current_annual_income(years_elapsed, market.inflation_rate) * (float(interest_and_salary_every_num_days) / DAYS_PER_YEAR)
            
            if verbosity > 1:
                if day % 1000 == 0:
                    print "Day " + str(day) + ", year " + str(years_elapsed) ,

            # regular account just buys ETF
            regular_account.buy_ETF(pay, day)

            # matched 401k account buys ETF with employee and employer funds
            matched_401k_account.buy_ETF(pay * (1+investor.match_percent_from_401k/100.0), day)

            # The next steps are for the margin account. It
            # 1. pays interest
            # 2. pays some principal on loans
            # 3. pay down margin if it's over limit
            # 4. buys new ETF with the remaining $

            # 1. pay interest
            interest = margin_account.compute_interest(market.annual_margin_interest_rate,interest_and_salary_every_fraction_of_year)
            pay_after_interest = pay - interest
            if pay_after_interest <= 0:
                margin_account.margin += (interest - pay) # amount of interest remaining
                margin_account.voluntary_rebalance(day, investor.tax_rates) # pay for the interest with equity
                #print """I didn't think hard about this case, since it's rare, so check back if I ever enter it. It's also bad tax-wise to rebalance, so try to avoid doing this."""
                # It's bad to rebalance using equity because of 1. capital-gains tax 2. transactions costs 3. bid-ask spreads
                # if this happens, no money left to 2. pay principal, 3. pay down margin if it's over limit, or 4. buy ETF
            else:
                # 2. pay some principal
                number_of_pay_periods_until_donation_date = (days_from_start_to_donation_date - day) / interest_and_salary_every_num_days
                amount_of_principal_to_repay = util.per_period_annuity_payment_of_principal(margin_account.margin, number_of_pay_periods_until_donation_date,market.annual_margin_interest_rate, investor.pay_principal_throughout)
                if amount_of_principal_to_repay > pay_after_interest:
                    margin_account.margin -= pay_after_interest
                    margin_account.voluntary_rebalance(day, investor.tax_rates) # pay for the principal with equity
                    #print "WARNING: You're paying for principal with equity. This incurs tax costs and so should be minimized!"
                    # It's bad to rebalance using equity because of 1. capital-gains tax 2. transactions costs 3. bid-ask spreads
                else:
                    margin_account.margin -= amount_of_principal_to_repay
                    pay_after_interest_and_principal = pay_after_interest - amount_of_principal_to_repay
                    # 3. pay down margin if it's over limit
                    amount_to_pay_for_margin_call = margin_account.debt_to_pay_off_to_restore_voluntary_max_margin_to_assets_ratio()
                    if amount_to_pay_for_margin_call > pay_after_interest_and_principal:
                        # pay what we can
                        margin_account.margin -= pay_after_interest_and_principal
                        # use equity for the rest
                        margin_account.voluntary_rebalance(day, investor.tax_rates)
                    else:
                        # just pay off margin call
                        margin_account.margin -= amount_to_pay_for_margin_call
                        pay_after_interest_and_principal_and_margincall = pay_after_interest_and_principal - amount_to_pay_for_margin_call
                        # 4. buy some ETF
                        margin_account.buy_ETF(pay_after_interest_and_principal_and_margincall, day)
            
            # If we're rebalancing upwards to increase leverage when it's too low, do that.
            if investor.rebalance_monthly_to_increase_leverage:
                margin_account.rebalance_to_increase_leverage(day)

            # Possibly get laid off or return to work
            investor.randomly_update_employment_status_this_month()

    # Now that we've donated, finish up
    margin_account.pay_off_all_margin(days_from_start_to_donation_date, investor.tax_rates)

    if regular_account.assets < TINY_NUMBER:
        print "WARNING: In this simulation round, the regular account ended with only ${}.".format(regular_account.assets)

    # Return present values of the account balances
    return (market.real_present_value(regular_account.assets,investor.years_until_donate),
            market.real_present_value(margin_account.assets,investor.years_until_donate),
            market.real_present_value(matched_401k_account.assets,investor.years_until_donate),
            historical_margin_to_assets_ratios, historical_margin_wealth)

def run_samples(investor,market,verbosity,num_samples,outfilepath=None):
    account_values = dict()
    account_types = ["regular", "margin", "matched401k"]
    NUM_HISTORIES_TO_PLOT = 20
    PRINT_PROGRESS_EVERY_ITERATIONS = 10
    margin_to_assets_ratio_histories = []
    wealth_histories = []
    running_average_margin_to_assets_ratios = None
    for type in account_types:
        account_values[type] = []
    for sample in range(num_samples):
        (regular_val, margin_val, matched_401k_val, margin_to_assets_ratios, margin_wealth) = one_run(investor,market,verbosity)
        account_values["regular"].append(regular_val)
        account_values["margin"].append(margin_val)
        account_values["matched401k"].append(matched_401k_val)

        if len(margin_to_assets_ratio_histories) < NUM_HISTORIES_TO_PLOT:
            margin_to_assets_ratio_histories.append(margin_to_assets_ratios)
        if len(wealth_histories) < NUM_HISTORIES_TO_PLOT:
            wealth_histories.append(margin_wealth)
        if running_average_margin_to_assets_ratios is None:
            running_average_margin_to_assets_ratios = copy.copy(margin_to_assets_ratios)
        else:
            running_average_margin_to_assets_ratios += margin_to_assets_ratios

        if verbosity > 0:
            if sample % PRINT_PROGRESS_EVERY_ITERATIONS == 0:
                print "Finished sample " + str(sample)

    avg_margin_to_assets_ratios = running_average_margin_to_assets_ratios / num_samples

    print ""
    print_and_write.print_means(account_values, investor.years_until_donate)
    print_and_write.print_percentiles(account_values)
    print_and_write.print_winner_for_each_percentile(account_values)
    
    if outfilepath:
        with open(outfilepath + ".txt", "w") as outfile:
            print_and_write.write_file_table(account_values, account_types, outfile)
        plots.graph_results(account_values, num_samples, outfilepath)
        plots.graph_historical_margin_to_assets_ratios(margin_to_assets_ratio_histories, avg_margin_to_assets_ratios, outfilepath)
        plots.graph_historical_wealth_trajectories(wealth_histories, outfilepath)

def sweep_scenarios():
    QUICK_TEST = False

    if QUICK_TEST:
        YEARS = 1
    else:
        YEARS = 30
    MU = .054
    SIGMA = .22
    INTEREST_RATE = .015
    INFLATION_RATE = .03
    USE_VIX_DATA = False
    STARTING_ANNUAL_INCOME = 30000
    INCOME_GROWTH_PERCENT = 2
    MATCH_FOR_401K = 50
    SHORT_TERM_CAP_GAINS = .28
    LONG_TERM_CAP_GAINS = .15
    STATE_INCOME_TAX = .05
    REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE = False
    PAY_PRINCIPAL_THROUGHOUT = True
    MAX_MARGIN_TO_ASSETS_RATIO = .5
    MONTHLY_PROBABILITY_OF_LAYOFF = .01
    MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF = .2
    NUM_TRIALS = 1000
    #NUM_TRIALS = 2
    VERBOSITY = 1

    tax_rates = TaxRates.TaxRates(SHORT_TERM_CAP_GAINS,LONG_TERM_CAP_GAINS,STATE_INCOME_TAX)

    print "\n\n\nDefault scenario"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    PAY_PRINCIPAL_THROUGHOUT, MAX_MARGIN_TO_ASSETS_RATIO, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,SIGMA,INTEREST_RATE,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\default_{}".format(QUICK_TEST))

    print "\n\n\nRebalance to increase leverage"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, True, 
                                    False, MAX_MARGIN_TO_ASSETS_RATIO, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,SIGMA,INTEREST_RATE,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\inclev_{}".format(QUICK_TEST))

    print "\n\n\nUse VIX data"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    PAY_PRINCIPAL_THROUGHOUT, MAX_MARGIN_TO_ASSETS_RATIO, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,SIGMA,INTEREST_RATE,INFLATION_RATE,True)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\VIX_{}".format(QUICK_TEST))

    print "\n\n\nDon't pay principal until end"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    False, MAX_MARGIN_TO_ASSETS_RATIO, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,SIGMA,INTEREST_RATE,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\princ_end_{}".format(QUICK_TEST))


    print "\n\n\ntesting 3X leverage"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    PAY_PRINCIPAL_THROUGHOUT, .67, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,SIGMA,INTEREST_RATE,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\lev=3X_{}".format(QUICK_TEST))

    print "\n\n\ntesting sigma"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    PAY_PRINCIPAL_THROUGHOUT, MAX_MARGIN_TO_ASSETS_RATIO, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,.4,INTEREST_RATE,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\sig4_{}".format(QUICK_TEST))

    print "\n\n\ntesting mu"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    PAY_PRINCIPAL_THROUGHOUT, MAX_MARGIN_TO_ASSETS_RATIO, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(.07,SIGMA,INTEREST_RATE,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\mu07_{}".format(QUICK_TEST))

    print "\n\n\ntesting interest rate"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    PAY_PRINCIPAL_THROUGHOUT, MAX_MARGIN_TO_ASSETS_RATIO, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,SIGMA,.03,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\int_r03_{}".format(QUICK_TEST))

    print "\n\n\ntesting 10 years"
    investor = Investor.Investor(10, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    PAY_PRINCIPAL_THROUGHOUT, MAX_MARGIN_TO_ASSETS_RATIO, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,SIGMA,INTEREST_RATE,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\yrs=10_{}".format(QUICK_TEST))


    print "\n\n\nBroker max margin-to-assets = .75"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    PAY_PRINCIPAL_THROUGHOUT, .75, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,SIGMA,INTEREST_RATE,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\lev75_{}".format(QUICK_TEST))


    print "\n\n\nBroker max margin-to-assets = .9"
    investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                    INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                    tax_rates, REBALANCE_MONTHLY_TO_INCREASE_LEVERAGE, 
                                    PAY_PRINCIPAL_THROUGHOUT, .9, 
                                    MONTHLY_PROBABILITY_OF_LAYOFF, MONTHLY_PROBABILITY_FIND_WORK_AFTER_LAID_OFF)
    market = Market.Market(MU,SIGMA,INTEREST_RATE,INFLATION_RATE,USE_VIX_DATA)
    run_samples(investor,market,VERBOSITY,NUM_TRIALS,"out\lev90_{}".format(QUICK_TEST))

if __name__ == "__main__":
    DO_SWEEP = True
    if DO_SWEEP:
        sweep_scenarios()
    else:
        tax_rates = TaxRates.TaxRates(.28, .15, .05)
        investor = Investor.Investor(1, 30000, 2, 50, tax_rates, False, True, .67, .01, .2)
        market = Market.Market(.054,.22,.015,.03,True)
        run_samples(investor,market,1,1000,None)