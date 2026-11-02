# Run from the repository root: Rscript examples/minimal.R
source('r/interpn_spline.R')
x <- c(0,1,2,4,7); y <- c(-2,0,1,3,4,6)
V <- outer(0:4,0:5,function(i,j)(10+((i+2)*(j+3))%%11)/100)
q <- rbind(c(1.5,.5),c(3.25,2.5),c(6.75,5.5))
actual <- interpn_spline(list(x,y),V,q)
expected <- c(838733/5632000,2031089/13926400,10632481/69632000)
stopifnot(all(abs(actual-expected)<2e-14+2e-13*abs(expected)))
print(actual,digits=17)
