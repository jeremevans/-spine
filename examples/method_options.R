# Run from the repository root: Rscript examples/method_options.R
source('r/interpolate_surface.R')
m<-c(.8,.95,1.05,1.2);t<-c(.1,.5,1,2)
g<-expand.grid(m,t);iv<-.2+.15*(g[,1]-1)^2+.04*exp(-g[,2])
q<-rbind(c(.9,.3),c(1,.75),c(1.1,1.5))
for(method in c('spline','linear','nadaraya_watson')) {
  fitted<-interpolate_surface(list(m,t),iv,q,method,
    bandwidth=if(method=='nadaraya_watson')c(.08,.3) else NULL)
  stopifnot(all(is.finite(fitted)),all(fitted>0))
  cat(method,'IV:',fitted,'log IV:',log(fitted),'\n')
}
