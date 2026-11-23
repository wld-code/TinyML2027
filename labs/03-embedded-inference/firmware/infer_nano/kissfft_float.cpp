// Compile en float la FFT kissfft fournie par la bibliothèque officielle
// Arduino_TensorFlowLite (third_party/kissfft). La bibliothèque procède de la même
// façon pour sa version entière (tensorflow/lite/experimental/microfrontend/lib/kiss_fft_int16.cpp).
// Aucun code FFT n'est écrit ici : on inclut les sources officielles telles quelles.
#include "third_party/kissfft/kiss_fft.c"
#include "third_party/kissfft/tools/kiss_fftr.c"
