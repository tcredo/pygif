#include <stdio.h>
#include <math.h>
#include <Python.h>
#include <arrayobject.h>

typedef unsigned char uint8;

static PyObject* cutils_reduceColor(PyObject *self, PyObject *args) {
	PyArrayObject *f;
	int levels;
	int dither = 1;
	PyArrayObject *result;
	if (!PyArg_ParseTuple(args,"Oi|i",&f,&levels,&dither))
	{
		PyErr_SetString(PyExc_ValueError,"Argument error!");
		return NULL;
	}
	if (f->nd!=2)
	{
		PyErr_SetString(PyExc_ValueError,"Array must be two dimensional.");
		return NULL;
	}
	if (f->descr->type_num!=PyArray_DOUBLE)
	{
		PyErr_SetString(PyExc_ValueError,"Array must be doubles.");
		return NULL;
	}
	int w = f->dimensions[0];
        int h = f->dimensions[1];
        double data[w][h];
        int x, y;
	for (x=0;x<w;x++)
	{
		for (y=0;y<h;y++)
		{
			data[x][y] = *(double *)(f->data + x*f->strides[0] + y*f->strides[1]);
		}
	}
	int dimensions[2] = {w,h};
	result = (PyArrayObject *)PyArray_FromDims(2,dimensions,PyArray_INT);
	PyObject *arrayElement;
        long l;
	char *address;
	double error;
	double conversion = (levels-1)/255.0;
	for (y=0;y<h;y++)
	{
		for (x=0;x<w;x++)
		{
			l = (long) (conversion*data[x][y]+0.5);
			error = data[x][y]-(l/conversion);
			if (dither>0) {
				if (x+1<w) data[x+1][y]=data[x+1][y]+0.4375*error;
				if (y+1<h)
				{
					if (x>0) data[x-1][y+1]=data[x-1][y+1]+0.1875*error;
					data[x][y+1]=data[x][y+1]+0.3125*error;
					if (x+1<w) data[x+1][y+1]=data[x+1][y+1]+0.0625*error;
				}
			}
			arrayElement = PyInt_FromLong(l);
			address = result->data + x*result->strides[0] + y*result->strides[1];
			result->descr->f->setitem(arrayElement,address,result);
			Py_DECREF(arrayElement);
		}
	}
	return Py_BuildValue("N",PyArray_Return(result));
}

static PyMethodDef ExtMethods[] = {
	{"reduceColor",cutils_reduceColor,METH_VARARGS,
	 "reduceColor(f,levels):\n"
	 "Posterize f with specified number of levels."},
	{NULL,NULL,0,NULL}
};

PyMODINIT_FUNC initcutils(void)
{
	(void) Py_InitModule("cutils",ExtMethods);
	import_array();
}

int main(int argc,char** argv)
{
	Py_Initialize();
	initcutils();
	return 0;
}
