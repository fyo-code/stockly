# Iteration 5A — V2 Naive Benchmark Scorecard

Generated: 2026-05-11 19:53

Runs: `v2_naive_fullgrid_2024-04-29`, `v2_naive_fullgrid_2024-05-27`, `v2_naive_fullgrid_2024-07-01`, `v2_naive_fullgrid_2024-07-29`, `v2_naive_fullgrid_2024-08-26`, `v2_naive_fullgrid_2024-09-23`, `v2_naive_fullgrid_2024-10-28`, `v2_naive_fullgrid_2024-11-25`, `v2_naive_fullgrid_2024-12-30`, `v2_naive_fullgrid_2025-01-27`, `v2_naive_fullgrid_2025-02-24`, `v2_naive_fullgrid_2025-03-24`

## Aggregate Headline Benchmark

Forecastable revenue movers across all 12 target windows:

| Model | Population rows | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| median_naive | 26,558 | 12,347 | 20.1% | 30.7% | 57.8% | -23.2% | 71.5% |
| roll13_mean | 26,558 | 12,347 | 20.3% | 30.3% | 60.9% | -14.1% | 71.1% |
| roll8_mean | 26,558 | 12,347 | 19.2% | 29.7% | 63.8% | -13.2% | 69.0% |
| seasonal52 | 26,558 | 12,347 | 15.5% | 23.5% | 69.1% | -34.3% | 72.2% |
| last4 | 26,558 | 12,347 | 17.4% | 26.4% | 69.7% | -13.0% | 61.4% |
| zero | 26,558 | 12,347 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |

Use `median_naive` as the first official v2-native baseline because it has the best aggregate WMAPE and the best hit +/-30 among simple methods. Its hit +/-20 is nearly tied with `roll13_mean`, but `roll13_mean` has worse WMAPE.

## Headline Forecastable Revenue Movers

| Run | Model | Eligible | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_naive_fullgrid_2024-04-29 | last4 | 1,981 | 771 | 18.7% | 27.0% | 66.1% | 4.7% | 66.4% |
| v2_naive_fullgrid_2024-04-29 | median_naive | 1,981 | 771 | 18.3% | 29.6% | 55.5% | -9.8% | 79.0% |
| v2_naive_fullgrid_2024-04-29 | roll13_mean | 1,981 | 771 | 18.5% | 30.1% | 61.4% | 4.8% | 79.0% |
| v2_naive_fullgrid_2024-04-29 | roll8_mean | 1,981 | 771 | 21.3% | 31.4% | 62.7% | 5.0% | 71.4% |
| v2_naive_fullgrid_2024-04-29 | seasonal52 | 1,981 | 771 | 12.3% | 19.1% | 74.6% | -40.1% | 75.0% |
| v2_naive_fullgrid_2024-04-29 | zero | 1,981 | 771 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2024-05-27 | last4 | 2,028 | 891 | 14.9% | 23.9% | 69.4% | -25.2% | 64.9% |
| v2_naive_fullgrid_2024-05-27 | median_naive | 2,028 | 891 | 18.7% | 27.5% | 60.9% | -30.0% | 75.7% |
| v2_naive_fullgrid_2024-05-27 | roll13_mean | 2,028 | 891 | 18.7% | 27.8% | 57.6% | -16.6% | 71.7% |
| v2_naive_fullgrid_2024-05-27 | roll8_mean | 2,028 | 891 | 16.9% | 26.7% | 61.8% | -18.3% | 70.9% |
| v2_naive_fullgrid_2024-05-27 | seasonal52 | 2,028 | 891 | 14.8% | 22.4% | 70.0% | -41.9% | 72.7% |
| v2_naive_fullgrid_2024-05-27 | zero | 2,028 | 891 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2024-07-01 | last4 | 2,100 | 889 | 20.8% | 31.7% | 67.9% | 3.0% | 59.2% |
| v2_naive_fullgrid_2024-07-01 | median_naive | 2,100 | 889 | 25.3% | 37.8% | 54.0% | -12.9% | 72.9% |
| v2_naive_fullgrid_2024-07-01 | roll13_mean | 2,100 | 889 | 24.3% | 35.7% | 56.2% | -5.1% | 72.6% |
| v2_naive_fullgrid_2024-07-01 | roll8_mean | 2,100 | 889 | 24.0% | 37.5% | 56.8% | -4.5% | 68.4% |
| v2_naive_fullgrid_2024-07-01 | seasonal52 | 2,100 | 889 | 15.9% | 24.2% | 68.4% | -36.9% | 73.8% |
| v2_naive_fullgrid_2024-07-01 | zero | 2,100 | 889 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2024-07-29 | last4 | 2,143 | 951 | 16.8% | 29.0% | 60.8% | -10.0% | 60.5% |
| v2_naive_fullgrid_2024-07-29 | median_naive | 2,143 | 951 | 20.9% | 34.4% | 51.7% | -20.9% | 69.4% |
| v2_naive_fullgrid_2024-07-29 | roll13_mean | 2,143 | 951 | 22.6% | 34.6% | 56.6% | -6.3% | 68.9% |
| v2_naive_fullgrid_2024-07-29 | roll8_mean | 2,143 | 951 | 19.8% | 29.7% | 59.3% | -2.5% | 65.3% |
| v2_naive_fullgrid_2024-07-29 | seasonal52 | 2,143 | 951 | 17.2% | 27.2% | 67.7% | -42.8% | 69.1% |
| v2_naive_fullgrid_2024-07-29 | zero | 2,143 | 951 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2024-08-26 | last4 | 2,204 | 1,207 | 17.8% | 27.6% | 62.0% | -32.1% | 60.1% |
| v2_naive_fullgrid_2024-08-26 | median_naive | 2,204 | 1,207 | 19.1% | 30.7% | 53.2% | -34.7% | 67.5% |
| v2_naive_fullgrid_2024-08-26 | roll13_mean | 2,204 | 1,207 | 19.4% | 29.6% | 52.8% | -27.0% | 62.0% |
| v2_naive_fullgrid_2024-08-26 | roll8_mean | 2,204 | 1,207 | 17.8% | 29.5% | 56.1% | -31.4% | 62.3% |
| v2_naive_fullgrid_2024-08-26 | seasonal52 | 2,204 | 1,207 | 15.1% | 24.4% | 65.1% | -38.2% | 77.0% |
| v2_naive_fullgrid_2024-08-26 | zero | 2,204 | 1,207 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2024-09-23 | last4 | 2,265 | 1,175 | 23.1% | 31.9% | 56.3% | -11.7% | 62.0% |
| v2_naive_fullgrid_2024-09-23 | median_naive | 2,265 | 1,175 | 23.6% | 34.1% | 51.4% | -27.4% | 67.7% |
| v2_naive_fullgrid_2024-09-23 | roll13_mean | 2,265 | 1,175 | 23.4% | 35.4% | 51.5% | -27.1% | 65.8% |
| v2_naive_fullgrid_2024-09-23 | roll8_mean | 2,265 | 1,175 | 25.4% | 37.7% | 51.9% | -23.2% | 66.8% |
| v2_naive_fullgrid_2024-09-23 | seasonal52 | 2,265 | 1,175 | 15.1% | 22.4% | 72.3% | -39.0% | 71.7% |
| v2_naive_fullgrid_2024-09-23 | zero | 2,265 | 1,175 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2024-10-28 | last4 | 2,287 | 1,628 | 13.1% | 20.1% | 60.4% | -50.6% | 50.8% |
| v2_naive_fullgrid_2024-10-28 | median_naive | 2,287 | 1,628 | 11.9% | 19.3% | 59.4% | -53.9% | 60.2% |
| v2_naive_fullgrid_2024-10-28 | roll13_mean | 2,287 | 1,628 | 10.7% | 17.3% | 61.3% | -54.3% | 63.7% |
| v2_naive_fullgrid_2024-10-28 | roll8_mean | 2,287 | 1,628 | 13.1% | 22.2% | 59.7% | -51.2% | 60.2% |
| v2_naive_fullgrid_2024-10-28 | seasonal52 | 2,287 | 1,628 | 17.6% | 26.8% | 61.8% | -44.8% | 73.4% |
| v2_naive_fullgrid_2024-10-28 | zero | 2,287 | 1,628 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2024-11-25 | last4 | 2,327 | 822 | 10.7% | 16.4% | 146.3% | 92.0% | 77.3% |
| v2_naive_fullgrid_2024-11-25 | median_naive | 2,327 | 822 | 19.0% | 28.1% | 83.6% | 25.3% | 80.7% |
| v2_naive_fullgrid_2024-11-25 | roll13_mean | 2,327 | 822 | 20.1% | 28.1% | 84.6% | 26.0% | 83.5% |
| v2_naive_fullgrid_2024-11-25 | roll8_mean | 2,327 | 822 | 12.8% | 21.3% | 102.6% | 45.9% | 82.4% |
| v2_naive_fullgrid_2024-11-25 | seasonal52 | 2,327 | 822 | 13.5% | 21.2% | 67.1% | -45.3% | 55.2% |
| v2_naive_fullgrid_2024-11-25 | zero | 2,327 | 822 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2024-12-30 | last4 | 2,345 | 907 | 14.1% | 21.3% | 94.0% | 5.1% | 49.4% |
| v2_naive_fullgrid_2024-12-30 | median_naive | 2,345 | 907 | 20.2% | 29.8% | 69.3% | 3.2% | 68.1% |
| v2_naive_fullgrid_2024-12-30 | roll13_mean | 2,345 | 907 | 21.6% | 30.5% | 78.6% | 35.6% | 73.2% |
| v2_naive_fullgrid_2024-12-30 | roll8_mean | 2,345 | 907 | 19.5% | 30.2% | 94.4% | 57.8% | 74.0% |
| v2_naive_fullgrid_2024-12-30 | seasonal52 | 2,345 | 907 | 16.8% | 23.5% | 81.3% | -13.6% | 74.7% |
| v2_naive_fullgrid_2024-12-30 | zero | 2,345 | 907 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2025-01-27 | last4 | 2,303 | 1,073 | 16.9% | 26.5% | 61.8% | -18.1% | 54.6% |
| v2_naive_fullgrid_2025-01-27 | median_naive | 2,303 | 1,073 | 22.8% | 34.6% | 54.4% | -6.3% | 67.1% |
| v2_naive_fullgrid_2025-01-27 | roll13_mean | 2,303 | 1,073 | 27.4% | 38.9% | 65.9% | 24.3% | 68.5% |
| v2_naive_fullgrid_2025-01-27 | roll8_mean | 2,303 | 1,073 | 18.4% | 26.3% | 70.3% | -12.0% | 58.1% |
| v2_naive_fullgrid_2025-01-27 | seasonal52 | 2,303 | 1,073 | 15.3% | 22.0% | 73.6% | -16.9% | 76.7% |
| v2_naive_fullgrid_2025-01-27 | zero | 2,303 | 1,073 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2025-02-24 | last4 | 2,296 | 977 | 20.8% | 29.6% | 62.3% | -15.9% | 64.4% |
| v2_naive_fullgrid_2025-02-24 | median_naive | 2,296 | 977 | 23.7% | 33.3% | 53.8% | -26.0% | 70.7% |
| v2_naive_fullgrid_2025-02-24 | roll13_mean | 2,296 | 977 | 20.2% | 30.2% | 63.0% | -16.8% | 65.9% |
| v2_naive_fullgrid_2025-02-24 | roll8_mean | 2,296 | 977 | 20.3% | 31.1% | 56.6% | -20.3% | 67.9% |
| v2_naive_fullgrid_2025-02-24 | seasonal52 | 2,296 | 977 | 17.3% | 23.8% | 69.0% | -18.7% | 76.2% |
| v2_naive_fullgrid_2025-02-24 | zero | 2,296 | 977 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_fullgrid_2025-03-24 | last4 | 2,279 | 1,056 | 21.1% | 32.7% | 54.0% | -21.0% | 61.0% |
| v2_naive_fullgrid_2025-03-24 | median_naive | 2,279 | 1,056 | 21.6% | 34.8% | 48.9% | -24.1% | 70.8% |
| v2_naive_fullgrid_2025-03-24 | roll13_mean | 2,279 | 1,056 | 22.3% | 32.5% | 47.7% | -24.0% | 67.7% |
| v2_naive_fullgrid_2025-03-24 | roll8_mean | 2,279 | 1,056 | 24.0% | 35.4% | 49.0% | -20.9% | 69.7% |
| v2_naive_fullgrid_2025-03-24 | seasonal52 | 2,279 | 1,056 | 13.6% | 22.2% | 71.4% | -17.7% | 78.1% |
| v2_naive_fullgrid_2025-03-24 | zero | 2,279 | 1,056 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |

## Median Naive By Regime

| Run | Regime | Population | Qty scored | Hit +/-20 | WMAPE | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- |
| v2_naive_fullgrid_2024-04-29 | active_movers | 886 | 326 | 16.3% | 64.2% | 71.3% |
| v2_naive_fullgrid_2024-04-29 | dormant | 21,654 | 28 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2024-04-29 | forecastable_revenue_movers | 1,981 | 771 | 18.3% | 55.5% | 79.0% |
| v2_naive_fullgrid_2024-04-29 | long_tail_active | 34,394 | 894 | 6.9% | 80.6% | 6.6% |
| v2_naive_fullgrid_2024-04-29 | seasonal_revenue_movers | 733 | 48 | 8.3% | 103.1% | 21.1% |
| v2_naive_fullgrid_2024-04-29 | sparse_revenue_items | 5,611 | 299 | 15.1% | 68.0% | 15.4% |
| v2_naive_fullgrid_2024-05-27 | active_movers | 929 | 315 | 16.2% | 68.1% | 64.7% |
| v2_naive_fullgrid_2024-05-27 | dormant | 22,320 | 36 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2024-05-27 | forecastable_revenue_movers | 2,028 | 891 | 18.7% | 60.9% | 75.7% |
| v2_naive_fullgrid_2024-05-27 | long_tail_active | 34,901 | 849 | 3.4% | 83.9% | 5.5% |
| v2_naive_fullgrid_2024-05-27 | seasonal_revenue_movers | 753 | 53 | 1.9% | 75.3% | 24.6% |
| v2_naive_fullgrid_2024-05-27 | sparse_revenue_items | 5,720 | 379 | 7.4% | 70.5% | 14.6% |
| v2_naive_fullgrid_2024-07-01 | active_movers | 978 | 373 | 14.7% | 71.9% | 60.7% |
| v2_naive_fullgrid_2024-07-01 | dormant | 23,486 | 30 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2024-07-01 | forecastable_revenue_movers | 2,100 | 889 | 25.3% | 54.0% | 72.9% |
| v2_naive_fullgrid_2024-07-01 | long_tail_active | 35,485 | 806 | 4.1% | 85.0% | 5.3% |
| v2_naive_fullgrid_2024-07-01 | seasonal_revenue_movers | 750 | 46 | 2.2% | 74.5% | 21.8% |
| v2_naive_fullgrid_2024-07-01 | sparse_revenue_items | 5,699 | 332 | 9.9% | 64.2% | 16.0% |
| v2_naive_fullgrid_2024-07-29 | active_movers | 1,024 | 362 | 18.2% | 59.0% | 68.0% |
| v2_naive_fullgrid_2024-07-29 | dormant | 24,589 | 25 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2024-07-29 | forecastable_revenue_movers | 2,143 | 951 | 20.9% | 51.7% | 69.4% |
| v2_naive_fullgrid_2024-07-29 | long_tail_active | 35,716 | 815 | 3.6% | 84.8% | 5.0% |
| v2_naive_fullgrid_2024-07-29 | seasonal_revenue_movers | 758 | 38 | 13.2% | 69.2% | 23.4% |
| v2_naive_fullgrid_2024-07-29 | sparse_revenue_items | 5,610 | 333 | 10.5% | 65.2% | 14.3% |
| v2_naive_fullgrid_2024-08-26 | active_movers | 1,085 | 445 | 15.3% | 62.9% | 64.5% |
| v2_naive_fullgrid_2024-08-26 | dormant | 25,638 | 52 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2024-08-26 | forecastable_revenue_movers | 2,204 | 1,207 | 19.1% | 53.2% | 67.5% |
| v2_naive_fullgrid_2024-08-26 | long_tail_active | 36,201 | 1,183 | 2.4% | 86.4% | 5.1% |
| v2_naive_fullgrid_2024-08-26 | seasonal_revenue_movers | 710 | 35 | 8.6% | 73.8% | 26.3% |
| v2_naive_fullgrid_2024-08-26 | sparse_revenue_items | 5,481 | 412 | 6.6% | 205.1% | 15.9% |
| v2_naive_fullgrid_2024-09-23 | active_movers | 1,164 | 446 | 15.7% | 66.9% | 69.2% |
| v2_naive_fullgrid_2024-09-23 | dormant | 26,884 | 35 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2024-09-23 | forecastable_revenue_movers | 2,265 | 1,175 | 23.6% | 51.4% | 67.7% |
| v2_naive_fullgrid_2024-09-23 | long_tail_active | 37,025 | 1,078 | 3.0% | 85.2% | 6.4% |
| v2_naive_fullgrid_2024-09-23 | seasonal_revenue_movers | 670 | 23 | 4.3% | 84.2% | 26.3% |
| v2_naive_fullgrid_2024-09-23 | sparse_revenue_items | 5,370 | 324 | 9.0% | 78.8% | 16.8% |
| v2_naive_fullgrid_2024-10-28 | active_movers | 1,231 | 684 | 11.1% | 63.5% | 61.1% |
| v2_naive_fullgrid_2024-10-28 | dormant | 28,365 | 85 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2024-10-28 | forecastable_revenue_movers | 2,287 | 1,628 | 11.9% | 59.4% | 60.2% |
| v2_naive_fullgrid_2024-10-28 | long_tail_active | 38,244 | 2,528 | 2.3% | 85.2% | 6.0% |
| v2_naive_fullgrid_2024-10-28 | seasonal_revenue_movers | 637 | 76 | 3.9% | 75.8% | 24.2% |
| v2_naive_fullgrid_2024-10-28 | sparse_revenue_items | 5,328 | 697 | 3.3% | 75.3% | 13.2% |
| v2_naive_fullgrid_2024-11-25 | active_movers | 1,354 | 495 | 17.4% | 66.3% | 71.1% |
| v2_naive_fullgrid_2024-11-25 | dormant | 30,365 | 24 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2024-11-25 | forecastable_revenue_movers | 2,327 | 822 | 19.0% | 83.6% | 80.7% |
| v2_naive_fullgrid_2024-11-25 | long_tail_active | 39,743 | 1,408 | 6.5% | 76.1% | 10.3% |
| v2_naive_fullgrid_2024-11-25 | seasonal_revenue_movers | 666 | 23 | 8.7% | 90.0% | 32.0% |
| v2_naive_fullgrid_2024-11-25 | sparse_revenue_items | 5,228 | 159 | 12.6% | 113.5% | 24.5% |
| v2_naive_fullgrid_2024-12-30 | active_movers | 1,395 | 455 | 19.8% | 63.1% | 68.4% |
| v2_naive_fullgrid_2024-12-30 | dormant | 31,879 | 30 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2024-12-30 | forecastable_revenue_movers | 2,345 | 907 | 20.2% | 69.3% | 68.1% |
| v2_naive_fullgrid_2024-12-30 | long_tail_active | 40,208 | 1,196 | 6.1% | 89.7% | 7.6% |
| v2_naive_fullgrid_2024-12-30 | seasonal_revenue_movers | 632 | 25 | 4.0% | 83.7% | 18.0% |
| v2_naive_fullgrid_2024-12-30 | sparse_revenue_items | 5,182 | 194 | 7.2% | 94.6% | 17.5% |
| v2_naive_fullgrid_2025-01-27 | active_movers | 1,387 | 473 | 18.8% | 57.6% | 68.5% |
| v2_naive_fullgrid_2025-01-27 | dormant | 33,262 | 27 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2025-01-27 | forecastable_revenue_movers | 2,303 | 1,073 | 22.8% | 54.4% | 67.1% |
| v2_naive_fullgrid_2025-01-27 | long_tail_active | 40,264 | 1,235 | 4.0% | 84.7% | 7.2% |
| v2_naive_fullgrid_2025-01-27 | seasonal_revenue_movers | 621 | 23 | 4.3% | 84.5% | 19.2% |
| v2_naive_fullgrid_2025-01-27 | sparse_revenue_items | 5,281 | 254 | 9.8% | 91.8% | 16.0% |
| v2_naive_fullgrid_2025-02-24 | active_movers | 1,394 | 420 | 16.9% | 61.6% | 63.9% |
| v2_naive_fullgrid_2025-02-24 | dormant | 34,787 | 31 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2025-02-24 | forecastable_revenue_movers | 2,296 | 977 | 23.7% | 53.8% | 70.7% |
| v2_naive_fullgrid_2025-02-24 | long_tail_active | 40,243 | 1,024 | 3.8% | 86.5% | 6.8% |
| v2_naive_fullgrid_2025-02-24 | seasonal_revenue_movers | 606 | 15 | 6.7% | 67.3% | 15.7% |
| v2_naive_fullgrid_2025-02-24 | sparse_revenue_items | 5,357 | 239 | 3.3% | 81.3% | 13.3% |
| v2_naive_fullgrid_2025-03-24 | active_movers | 1,398 | 503 | 13.3% | 63.2% | 63.5% |
| v2_naive_fullgrid_2025-03-24 | dormant | 35,987 | 21 | 0.0% | 100.0% | 0.0% |
| v2_naive_fullgrid_2025-03-24 | forecastable_revenue_movers | 2,279 | 1,056 | 21.6% | 48.9% | 70.8% |
| v2_naive_fullgrid_2025-03-24 | long_tail_active | 40,722 | 1,162 | 2.3% | 86.0% | 6.2% |
| v2_naive_fullgrid_2025-03-24 | seasonal_revenue_movers | 613 | 29 | 10.3% | 71.7% | 15.9% |
| v2_naive_fullgrid_2025-03-24 | sparse_revenue_items | 5,459 | 248 | 6.0% | 72.0% | 13.6% |

## Notes

- This is a v2-native chain-level benchmark, not a legacy Iter 3/4 comparison.
- Regime labels are recomputed with only data before each target window.
- Quantity hit metrics use material actual windows only: `actual_units >= 4`.
- Zero-heavy regimes should be judged by phantom/zero behavior, not headline hit rate.
