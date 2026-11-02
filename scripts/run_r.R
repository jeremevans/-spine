#!/usr/bin/env Rscript
# Tensor product of pracma's MATLAB-compatible not-a-knot 1D splines.
# This is deliberately not stats::spline(method='fmm') or a natural spline.
args <- commandArgs(trailingOnly=TRUE)
infile <- if (length(args)>=1) args[1] else 'fixtures/splines.json'
outfile <- if (length(args)>=2) args[2] else 'results/r.json'
if (!requireNamespace('jsonlite', quietly=TRUE) || !requireNamespace('pracma', quietly=TRUE))
  stop('Install jsonlite and pracma first')
data <- jsonlite::fromJSON(infile, simplifyVector=FALSE)

script_file <- sub("^--file=", "", grep("^--file=", commandArgs(), value=TRUE)[1])
source(file.path(dirname(dirname(normalizePath(script_file))),"r","interpn_spline.R"))

rows <- lapply(data$payload$cases,function(c) {
  axes <- lapply(c$axes,function(x)as.numeric(unlist(x)))
  q <- do.call(rbind,lapply(c$queries,unlist))
  fill <- if (is.character(c$fill)) NA_real_ else c$fill
  y <- interpn_spline(axes,as.numeric(unlist(c$values)),q,fill)
  list(name=c$name,values=unname(y))
})
out <- list(schema_version=1,engine='R',engine_version=R.version.string,
    pracma_version=as.character(utils::packageVersion('pracma')),
    jsonlite_version=as.character(utils::packageVersion('jsonlite')),
    fixture_id=data$fixture_id,method='tensor product of pracma::interp1 spline',results=rows)
dir.create(dirname(outfile),recursive=TRUE,showWarnings=FALSE)
jsonlite::write_json(out,outfile,auto_unbox=TRUE,digits=17,na='null',pretty=TRUE)
