# Not-a-knot tensor spline; values use R/MATLAB column-major order.
# Paired queries: one row per point; default out-of-domain result is NA.
interpn_spline <- function(axes, values, q, fill=NA_real_) {
  if (!requireNamespace("pracma", quietly=TRUE)) stop("Install pracma first")
  d <- length(axes)
  stopifnot(d>0, is.matrix(q), is.numeric(values), !is.complex(values),
            all(is.finite(values)), all(is.finite(q)), !is.complex(q))
  stopifnot(length(values)==prod(lengths(axes)),ncol(q)==d)
  outside <- rep(FALSE,nrow(q))
  weights <- vector('list',d)
  for (j in seq_len(d)) {
    x <- axes[[j]]
    stopifnot(!is.complex(x),length(x)>=4,all(diff(x)>0),all(is.finite(x)))
    outside <- outside | q[,j]<x[1] | q[,j]>x[length(x)]
    # pracma requires queries in-domain. Mask the excluded rows after evaluation.
    qq <- pmin(pmax(q[,j],x[1]),x[length(x)])
    I <- diag(length(x))
    weights[[j]] <- vapply(seq_along(x),function(k)
      pracma::interp1(x,I[,k],qq,method='spline'),numeric(nrow(q)))
  }
  ans <- numeric(nrow(q))
  for (i in seq_len(nrow(q))) {
    z <- values
    for (j in seq_len(d))
      z <- as.vector(crossprod(weights[[j]][i,],matrix(z,nrow=length(axes[[j]]))))
    ans[i] <- z
  }
  ans[outside] <- fill
  ans
}

