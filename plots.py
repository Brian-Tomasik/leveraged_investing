import numpy
import util
import operator
from matplotlib import pyplot
from os import path
import Market
import margin_leverage

OPTIMAL_LEVERAGE_GRAPH_PREFIX = "aaa_opt_lev" # add "aaa_" to put it first alphabetically so it's easier to find
EXPECTED_UTILITY_GRAPH_PREFIX = "exp_util"
EXPECTED_SATURATION_UTILITY_GRAPH_PREFIX = "exp_sat_util"

def graph_histograms(account_values, num_samples, outfilepath):
    alpha_for_pyplot = .5
    num_bins = max(10, num_samples/10)

    # Plot each histogram separately
    for type in ["regular", "margin", "matched401k"]:
        median_value = util.percentile(account_values[type], .5)
        numpy_array = numpy.array(account_values[type])
        bin_min = min(numpy_array)
        bin_max = min(max(numpy_array), 10 * median_value) # the "25 * median_value" part avoids having a distorted graph due to far-right skewed values
        graph_bins = numpy.linspace(bin_min, bin_max, num_bins)
        if type is "regular":
            regular_array = numpy_array
            regular_bins = graph_bins
        elif type is "margin":
            margin_array = numpy_array
            margin_bins = graph_bins
        pyplot.hist(numpy_array, bins=graph_bins, alpha=alpha_for_pyplot)
        pyplot.title("Distribution of results for " + type + " investing")
        pyplot.xlabel("Present value of donated $")
        pyplot.ylabel("Frequency out of " + str(num_samples) + " runs")
        pyplot.savefig(outfilepath + "_hist_" + type)
        pyplot.close()

    # Plot regular and margin together
    pyplot.hist(regular_array, bins=regular_bins, alpha=alpha_for_pyplot, label="regular")
    pyplot.hist(margin_array, bins=margin_bins, alpha=alpha_for_pyplot, label="margin")
    pyplot.title("Distribution of results: regular vs. margin")
    pyplot.xlabel("Present value of donated $")
    pyplot.ylabel("Frequency out of " + str(num_samples) + " runs")
    pyplot.legend()
    pyplot.savefig(outfilepath + "_bothhist")
    pyplot.close()

def graph_expected_utility_vs_alpha(numpy_regular, numpy_margin, outdir_name):
    """alpha is as in utility(wealth) = wealth^alpha"""

    MIN_ALPHA = 0
    MAX_ALPHA = 1
    NUM_POINTS = 1000
    alpha_values = numpy.linspace(MIN_ALPHA,MAX_ALPHA,NUM_POINTS)
    ratio_of_expected_utilities = map(lambda alpha: \
        numpy.mean(map(lambda wealth: util.utility(wealth, alpha), numpy_margin)) / \
        numpy.mean(map(lambda wealth: util.utility(wealth, alpha), numpy_regular)),
                                      alpha_values)

    pyplot.plot(alpha_values,ratio_of_expected_utilities)
    pyplot.title("Ratio of margin/regular expected utility vs. risk tolerance, alpha")
    pyplot.xlabel("alpha: measure of risk tolerance, as in utility(wealth) = (wealth)^alpha")
    pyplot.ylabel("expected_utility(margin) / expected_utility(regular)")
    pyplot.savefig("%s_%s" % (outdir_name, EXPECTED_UTILITY_GRAPH_PREFIX))
    pyplot.close()

def graph_expected_utility_vs_wealth_saturation_cutoff(numpy_regular, numpy_margin, \
    outdir_name, min_log10_saturation, max_log10_saturation):
    NUM_POINTS = 1000
    saturation_values = numpy.logspace(min_log10_saturation,max_log10_saturation,NUM_POINTS)
    ratio_of_expected_utilities = map(lambda saturation: \
        numpy.mean(map(lambda wealth: util.saturation_utility(wealth, saturation), numpy_margin)) / \
        numpy.mean(map(lambda wealth: util.saturation_utility(wealth, saturation), numpy_regular)),
                                      saturation_values)
    fig = pyplot.figure()
    ax = fig.add_subplot(2,1,1) # see http://stackoverflow.com/a/1183415
    ax.plot(saturation_values,ratio_of_expected_utilities)
    ax.set_xscale('log')
    pyplot.title("Ratio of margin/regular expected saturation-utility vs. saturation cutoff")
    pyplot.xlabel("saturation cutoff: after what amount of money does the value of more level off?")
    pyplot.ylabel("exp_sat_utility(margin) / exp_sat_utility(regular)")
    pyplot.savefig("%s_%s" % (outdir_name, EXPECTED_SATURATION_UTILITY_GRAPH_PREFIX),bbox_inches='tight')
    pyplot.close()

def graph_historical_margin_to_assets_ratios(collection_of_ratios, avg_ratios, outfilepath):
    num_days = len(avg_ratios)
    x_axis = [float(day)/margin_leverage.DAYS_PER_YEAR for day in xrange(num_days)]

    # Plot individual trajectories
    for individual in collection_of_ratios:
        assert len(individual) == num_days, "Inconsistent number of days in history vectors"
        pyplot.plot(x_axis, individual)
    pyplot.title("Individual trajectories of margin-to-assets ratios vs. year of simulation")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Margin-to-assets ratio")
    pyplot.savefig(outfilepath + "_indMTA")
    pyplot.close()

    # Plot average trajectory
    pyplot.plot(x_axis, avg_ratios)
    pyplot.title("Average trajectory of margin-to-assets ratios vs. year of simulation")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Average margin-to-assets ratio")
    pyplot.savefig(outfilepath + "_avgMTA")
    pyplot.close()

def graph_historical_wealth_trajectories(wealth_histories, outfilepath):
    num_days = len(wealth_histories[0])
    x_axis = [float(day)/margin_leverage.DAYS_PER_YEAR for day in xrange(num_days)]

    # Plot individual trajectories
    for individual in wealth_histories:
        assert len(individual) == num_days, "Inconsistent number of days in history vectors"
        pyplot.plot(x_axis, individual)
    pyplot.title("Wealth trajectories vs. year of simulation")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Present value of donated $")
    pyplot.savefig(outfilepath + "_wealthtraj")
    pyplot.close()

def graph_carried_cap_gains_trajectories(carried_cap_gains_histories, outfilepath):
    num_days = len(carried_cap_gains_histories[0])
    x_axis = [float(day)/margin_leverage.DAYS_PER_YEAR for day in xrange(num_days)]

    # Plot individual trajectories
    for individual in carried_cap_gains_histories:
        assert len(individual) == num_days, "Inconsistent number of days in history vectors"
        pyplot.plot(x_axis, individual)
    pyplot.title("Carried capital gains/losses vs. year of simulation")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Carried short+long-term capital gains/losses ($)")
    pyplot.savefig(outfilepath + "_carrcg")
    pyplot.close()

def graph_percent_differences_from_simple_calc(percent_differences_from_simple_calc, 
                                               outfilepath):
    num_days = len(percent_differences_from_simple_calc[0])
    x_axis = [float(day)/margin_leverage.DAYS_PER_YEAR for day in xrange(num_days)]

    # Plot individual trajectories
    for trajectory in percent_differences_from_simple_calc:
        assert len(trajectory) == num_days, "Inconsistent number of days in history vectors"
        pyplot.plot(x_axis, trajectory)
    pyplot.title("% differences of margin account values vs. a naive calculation")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("% differences for various individual trajectories")
    pyplot.savefig(outfilepath + "_percdiff")
    pyplot.close()

def graph_trends_vs_leverage_amount(output_queue, outdir_name):
    """Graph to show optimal leverage."""

    # Sort the queue by the N leverage value
    output_tuples = []
    while not output_queue.empty():
        output_tuples.append(output_queue.get())
    output_tuples.sort(key=operator.itemgetter(0))

    # Get the axes
    attributes = dict()
    KEYS = ["Ns", "(E[wealth] margin)/(E[wealth] regular)", 
            "Error in means ratio", "(Median wealth margin)/(Median wealth regular)", 
            "(E[sqrt(wealth)] margin)/(E[sqrt(wealth)] regular)", 
            "Error in exp-sqrt-wealth ratio"]
    for key in KEYS:
        attributes[key] = []
    for tuple in output_tuples:
        assert len(KEYS) == len(tuple), "Tuple is wrong length"
        for i in xrange(len(tuple)):
            attributes[KEYS[i]].append(tuple[i])

    # Plot the axes
    x_axis = attributes["Ns"]
    fig,(ax1)=pyplot.subplots(1,1)

    key = "(E[wealth] margin)/(E[wealth] regular)"
    y_axis = attributes[key]
    yerr = attributes["Error in means ratio"]
    ax1.errorbar(x_axis, y_axis, yerr=yerr, label=key)
    min_y = min(y_axis)

    key = "(Median wealth margin)/(Median wealth regular)"
    y_axis = attributes[key]
    ax1.plot(x_axis, y_axis, label=key)
    min_y = min(min_y, min(y_axis))
    max_med_or_expsqrtwealth = max(y_axis)

    key = "(E[sqrt(wealth)] margin)/(E[sqrt(wealth)] regular)"
    y_axis = attributes[key]
    yerr = attributes["Error in exp-sqrt-wealth ratio"]
    ax1.errorbar(x_axis, y_axis, yerr=yerr, label=key)
    min_y = min(min_y, min(y_axis))
    max_med_or_expsqrtwealth = max(max_med_or_expsqrtwealth, max(y_axis))

    # Set axes
    pyplot.axis([min(x_axis)-.1, max(x_axis)+.1, 0, max_med_or_expsqrtwealth+1])

    """
    THIS DOESN'T SEEM TO WORK...
    # Here's logic to remove error bars from the legend.... 
    # http://stackoverflow.com/questions/14297714/matplotlib-dont-show-errorbars-in-legend
    # get handles
    handles, labels = ax1.get_legend_handles_labels()
    # remove the errorbars
    handles = [h[0] for h in handles] # GIVES AN EXCEPTION: 'Line2D' object does not support indexing
    # use them in the legend
    ax1.legend(handles, labels)
    """
    
    pyplot.title("Margin performance vs. amount of leverage")
    pyplot.xlabel("Amount of leverage (e.g., 2 means 2X leverage)")
    pyplot.ylabel("Ratio of margin account's value over regular account's value")
    pyplot.legend()
    pyplot.savefig(path.join(outdir_name,OPTIMAL_LEVERAGE_GRAPH_PREFIX))
    pyplot.close()

def theoretical_optimal_leverage_based_on_risk_tolerance(fig_name_including_path,
                                                         alpha_values,c_star_values):
    pyplot.plot(alpha_values, c_star_values)
    pyplot.title("Optimal theoretical leverage, c*, vs. degree of risk tolerance, alpha")
    pyplot.xlabel("alpha: measure of risk tolerance, as in utility(wealth) = (wealth)^alpha")
    pyplot.ylabel("c*: optimal leverage amount, like c* = 2 means 2X leverage is optimal")
    pyplot.savefig(fig_name_including_path)
    pyplot.close()

def graph_margin_vs_regular_trajectories(regular_wealths, margin_wealths, outfilepath, iter_num):
    num_days = len(regular_wealths)
    assert len(margin_wealths) == num_days, "Input arrays not the same length."
    default_market = Market.Market()
    x_axis = [float(day)/margin_leverage.DAYS_PER_YEAR for day in xrange(num_days)]

    pyplot.plot(x_axis, regular_wealths, label="regular")
    pyplot.plot(x_axis, margin_wealths, label="margin")
    pyplot.title("Trajectories of regular vs. margin investing for one simulation run")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Nominal asset value ($)")
    pyplot.legend()
    pyplot.savefig(outfilepath + "_regularvsmar_iter%i" % iter_num)
    pyplot.close()

def graph_lev_ETF_and_underlying_trajectories(regular_ETF, lev_ETF, outfilepath, iter_num):
    num_days = len(regular_ETF)
    assert len(lev_ETF) == num_days, "Input arrays not the same length."
    default_market = Market.Market()
    x_axis = [float(day)/default_market.trading_days_per_year for day in xrange(num_days)]

    pyplot.plot(x_axis, regular_ETF, label="regular ETF")
    pyplot.plot(x_axis, lev_ETF, label="leveraged ETF")
    pyplot.title("Trajectories of regular vs. leveraged ETF for one simulation run")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Nominal asset value ($)")
    pyplot.legend()
    pyplot.savefig(outfilepath + "_regularvslev_iter%i" % iter_num)
    pyplot.close()