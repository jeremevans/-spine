args <- commandArgs(trailingOnly=TRUE)
f <- jsonlite::fromJSON(args[1], simplifyVector=FALSE)
rows <- lapply(f$payload$cases, function(c) {
  X <- do.call(rbind, lapply(c$train_log, unlist))
  k <- c$k; mu <- colMeans(X); Z <- sweep(X, 2, mu)
  s <- svd(Z); L <- s$v[,seq_len(k),drop=FALSE]; scores <- Z %*% L
  adjacent <- diff(unlist(c$months)) == 1
  phi <- predicted <- numeric(k)
  for (j in seq_len(k)) {
    lag <- scores[-nrow(X),j]; lead <- scores[-1,j]
    B <- qr.solve(cbind(1,lag[adjacent]),lead[adjacent])
    phi[j] <- B[2]; predicted[j] <- B[1] + B[2]*scores[nrow(X),j]
  }
  list(name=c$name, forecast_log=as.vector(mu+L %*% predicted),
       projector=L %*% t(L),phi=phi,explained_ratio=s$d[seq_len(k)]^2/sum(s$d^2))
})
out <- list(engine='R',engine_version=R.version.string,fixture_id=f$fixture_id,cases=rows)
jsonlite::write_json(out,args[2],digits=17,auto_unbox=TRUE)
