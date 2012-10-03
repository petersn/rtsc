// Supporting standard library.

RTSC_true = true;
RTSC_false = false;

Array.prototype.RTSC_push = Array.prototype.push;
Array.prototype.RTSC_contains = function (x) {
	return x in this;
};

function range(begin, end) {
	result = [];
	for (i = begin; i < end; i++)
		result.push(i);
	return result;
}

