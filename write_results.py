import numpy
import util
import math

def write_means(account_values, years_until_donation_date, outfile):
    regular_mean = util.mean(account_values["regular"])
    margin_mean = util.mean(account_values["margin"])
    matched_401k_mean = util.mean(account_values["matched401k"])
    outfile.write("\n")
    outfile.write("Mean regular = ${:,}\n".format(int(round(regular_mean,0))))
    outfile.write("Mean margin = ${:,}\n".format(int(round(margin_mean,0))))
    outfile.write("Mean matched 401k = ${:,}\n".format(int(round(matched_401k_mean,0))))
    outfile.write("Mean value per year of margin over regular = ${:,}\n".format(int(round( (margin_mean-regular_mean)/years_until_donation_date, 0))))

def write_percentiles(account_values, outfile):
    for percentile in [0, 10, 25, 50, 75, 90, 100]:
        fractional_percentile = percentile/100.0
        outfile.write("\n")
        for type in ["regular", "margin", "matched401k"]:
            outfile.write( str(percentile) + "th percentile " + type + " = ${:,}\n".format(int(round(util.percentile(account_values[type], fractional_percentile),0))) )

def write_winner_for_each_percentile(account_values, outfile):
    index = 0
    sorted_regular_list = sorted(account_values["regular"])
    sorted_margin_list = sorted(account_values["margin"])
    assert len(sorted_regular_list) == len(sorted_margin_list), "Regular and margin lists not the same length"
    upper_index = len(sorted_regular_list) - 1
    outfile.write("\n")
    outfile.write("Margin vs. regular % at percentiles 0 to 100:\n")
    for percentile in range(100):
        index = int((percentile/100.0)*upper_index)
        if sorted_regular_list[index] > 0: # prevent divide-by-zero errors
            outfile.write( "{}% ".format(int(round( (100.0 * sorted_margin_list[index]) / sorted_regular_list[index], 0 ))) )

def write_file_table(account_values, account_types, bankruptcy_fraction, outfile):
    outfile.write("<table>\n")
    outfile.write("""<tr><td><i>Type</i></td> <td><i>Mean &plusmn; stderr</i></td> <td><i>Median</i></td> <td><i>Min</i></td> <td><i>Max</i></td> <td><i>E[&radic;(wealth)] &plusmn; stderr</i></td> <td><i>&sigma;<sub>log(wealth)</sub></i></td> </tr>\n""");
    for type in account_types:
        numpy_values = numpy.array(account_values[type])
        log_values = map(math.log, numpy_values+1) # The +1 here is so that the log() value will be at least 0
        sqrt_values = map(math.sqrt, numpy_values)
        outfile.write("<tr><td><i>{}</i></td> <td>${:,} &plusmn; ${:,}</td> <td>${:,}</td> <td>${:,}</td> <td>${:,}</td> <td>{:,} &plusmn; {:,}</td> <td>{:.2f}</td></tr>\n".format( 
            return_pretty_name_for_type(type), 
            int(round(numpy.mean(numpy_values),0)) , int(round(util.stderr(numpy_values),0)), 
            int(round(numpy.median(numpy_values),0)) , 
            int(round(util.percentile(account_values[type], 0),0)) , 
            int(round(util.percentile(account_values[type], 1),0)) ,
            int(round(numpy.mean(sqrt_values),0)), int(round(util.stderr(sqrt_values),0)), 
            numpy.std(log_values) ))
    outfile.write("</table>")
    outfile.write("\nMargin is better than regular {}% of the time. Margin resulted in bankruptcy {}% of the time.".format(
        int(round(100 * util.probability_x_better_than_y(
            account_values["margin"],account_values["regular"]),1)), 
        round(100 * bankruptcy_fraction,1)))

def return_pretty_name_for_type(type):
    if type == "regular":
        return "Regular"
    elif type == "margin":
        return "Margin"
    elif type == "matched401k":
        return "Regular + 50% match"
    else:
        raise Exception("Given type not valid")