// Fichier généré par python/convert.py : ne pas modifier à la main.
// Valeurs attendues = interpréteur LiteRT desktop (noyaux de référence).
#pragma once
constexpr int kNumTests = 23;
const float kTestX[kNumTests] = {0.0f, 0.314159274f, 0.628318548f, 0.942477822f, 1.2566371f, 1.57079637f, 1.88495564f, 2.1991148f, 2.51327419f, 2.82743335f, 3.14159274f, 3.4557519f, 3.76991129f, 4.08407068f, 4.3982296f, 4.71238899f, 5.02654839f, 5.3407073f, 5.6548667f, 5.96902609f, 6.28318548f, -0.5f, 7.0f};
const float kKerasY[kNumTests] = {0.0144940615f, 0.29804796f, 0.580272436f, 0.799631119f, 0.979703903f, 0.974537492f, 0.969371557f, 0.828254342f, 0.589338541f, 0.3062042f, -0.00371801853f, -0.313640118f, -0.623562396f, -0.798472285f, -0.92220962f, -1.04594672f, -0.932237625f, -0.73606962f, -0.539901912f, -0.343734145f, -0.147566199f, 0.0150014758f, 0.0208435059f};
constexpr int kTolLsb = 1;
const signed char kExpectedQ[kNumTests] = {6, 44, 78, 102, 125, 125, 124, 105, 73, 36, -2, -41, -83, -99, -115, -128, -109, -84, -60, -38, -14, 6, -14};
