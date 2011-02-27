from math import sqrt

def mean(values):
	return sum(values)/(len(values)*1.0)

def median(values):
	avg = mean(values)
	values = sorted(values)
	for k in range(len(values)-1):
		if values[k] < avg and values[k+1] > avg:
			return values[k]
	
	assert False, "Shouldn't get here"

# taken from http://www.phys.uu.nl/~haque/computing/WPark_recipes_in_python.html

"""
Calculate mean and standard deviation of data x[]:
	mean = {\sum_i x_i \over n}
	std = sqrt(\sum_i (x_i - mean)^2 \over n-1)
"""
def meanstdv(x):
	avg = mean(x)
	std = sum([(a - avg)**2 for a in x])
	std = sqrt(std / (len(x)*1.0))
	return avg, std
