// Supporting standard library.

RTSC_global = this;
RTSC_true = true;
RTSC_false = false;
RTSC_object_lists = {};

Array.prototype.RTSC_push = Array.prototype.push;
Array.prototype.RTSC_contains = function (x) {
	return x in this;
};

function defaultFillPrototype(proto) {
	proto.RTSC___init__ = function() {};
	proto.RTSC_hasType = function(other) {
		return this instanceof other;
	};
}

function RTSC_range(begin, end) {
	result = [];
	for (i = begin; i < end; i++)
		result.push(i);
	return result;
}

function RTSC_error(msg) {
	RTSC_print(msg);
}

