# Source this file to load all three grid methods plus scattered Gaussian NW.
source(file.path(dirname(normalizePath(sys.frame(1)$ofile)), "interpn_spline.R"))

.validate_grid <- function(axes, values, q, min_nodes=2) {
  stopifnot(length(axes)>0, is.matrix(q), ncol(q)==length(axes),
            is.numeric(values), !is.complex(values), !is.complex(q),
            all(is.finite(values)), all(is.finite(q)),
            length(values)==prod(lengths(axes)))
  for (x in axes) stopifnot(is.numeric(x), !is.complex(x),
    length(x)>=min_nodes, all(is.finite(x)), all(diff(x)>0))
}

interpn_linear <- function(axes, values, q, fill=NA_real_) {
  .validate_grid(axes, values, q)
  stopifnot(length(fill)==1, is.numeric(fill), !is.complex(fill))
  ans <- rep(fill,nrow(q))
  for (i in seq_len(nrow(q))) {
    if (any(vapply(seq_along(axes),function(j)
      q[i,j]<axes[[j]][1] || q[i,j]>tail(axes[[j]],1),logical(1)))) next
    z <- as.vector(values)
    for (j in seq_along(axes)) {
      x <- axes[[j]]; k <- min(findInterval(q[i,j],x),length(x)-1)
      t <- (q[i,j]-x[k])/(x[k+1]-x[k])
      w <- numeric(length(x)); w[k] <- 1-t; w[k+1] <- t
      z <- as.vector(crossprod(w,matrix(z,nrow=length(x))))
    }
    ans[i] <- z
  }
  ans
}

nadaraya_watson <- function(points, values, q, bandwidth) {
  stopifnot(is.matrix(points),nrow(points)>0,ncol(points)>0,
    is.matrix(q),ncol(q)==ncol(points),length(values)==nrow(points),
    is.numeric(values),!is.complex(values),!is.complex(points),!is.complex(q),
    all(is.finite(points)),all(is.finite(values)),all(is.finite(q)),
    is.numeric(bandwidth),!is.complex(bandwidth),all(is.finite(bandwidth)),
    all(bandwidth>0),length(bandwidth)%in%c(1,ncol(points)))
  h <- rep(bandwidth,length.out=ncol(points))
  ans <- numeric(nrow(q)); scale <- max(1,abs(values))
  for (i in seq_len(nrow(q))) {
    delta <- sweep(sweep(points,2,q[i,],'-'),2,h,'/')
    d2 <- rowSums(delta*delta)
    if (!all(is.finite(d2))) stop('Scaled distances overflow; rescale coordinates or bandwidths')
    lw <- -.5*d2; w <- exp(lw-max(lw)); w <- w/sum(w)
    ans[i] <- sum(w*(values/scale))*scale
  }
  ans
}

interpolate_surface <- function(axes, values, q, method='spline',
                                bandwidth=NULL, fill=NA_real_) {
  stopifnot(length(method)==1,method%in%c('spline','linear','nadaraya_watson'),
            length(fill)==1,is.numeric(fill),!is.complex(fill))
  .validate_grid(axes,values,q,if(method=='spline')4 else 2)
  if (method!='nadaraya_watson') {
    if (!is.null(bandwidth)) stop('bandwidth applies only to nadaraya_watson')
    if (method=='spline') return(interpn_spline(axes,values,q,fill))
    return(interpn_linear(axes,values,q,fill))
  }
  if (is.null(bandwidth)) stop('nadaraya_watson requires explicit bandwidths')
  points <- as.matrix(expand.grid(axes)) # first coordinate varies fastest
  inside <- rep(TRUE,nrow(q))
  for(j in seq_along(axes)) inside <- inside & q[,j]>=axes[[j]][1] & q[,j]<=tail(axes[[j]],1)
  ans <- rep(fill,nrow(q))
  ans[inside] <- nadaraya_watson(points,as.vector(values),q[inside,,drop=FALSE],bandwidth)
  ans
}
