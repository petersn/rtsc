// Supporting standard library.

Array.prototype.RTSC_push = Array.prototype.push;

function range(begin, end) {
	result = [];
	for (i = begin; i < end; i++)
		result.push(i);
	return result;
}

