#include <Python.h>
#include <arrayobject.h>
#include "reduce_color.c"

static PyMethodDef ExtMethods[] = {
  {"reduceColor", reduce_color, METH_VARARGS,
   "reduceColor(f,levels):\nPosterize f with specified number of levels."},
  {NULL,NULL,0,NULL}
};

PyMODINIT_FUNC initcutils(void) {
  (void) Py_InitModule("cutils", ExtMethods);
  import_array();
}
