#include <RcppArmadillo.h>
// [[Rcpp::depends(RcppArmadillo)]]

arma::vec sgolayfilt(const arma::vec& y, int window_size, int poly_order) {
  int half_window = (window_size - 1) / 2;
  arma::vec y_padded = arma::join_cols(arma::vec(half_window).fill(y(0)), y);
  y_padded = arma::join_cols(y_padded, arma::vec(half_window).fill(y(y.n_elem - 1)));
  
  arma::vec result(y.n_elem);
  arma::mat A(window_size, poly_order + 1);
  
  for(int i = 0; i < window_size; ++i) {
    for(int j = 0; j <= poly_order; ++j) {
      A(i, j) = std::pow(i - half_window, j);
    }
  }
  
  arma::mat A_trans = A.t();
  arma::mat A_trans_A_inv = inv(A_trans * A);
  arma::rowvec w = A_trans_A_inv.row(0) * A_trans;
  
  for(size_t i = half_window; i < y.n_elem + half_window; ++i) {
    arma::vec y_sub = y_padded.subvec(i - half_window, i + half_window);
    result[i - half_window] = arma::dot(w, y_sub);
  }
  
  return result;
}

// [[Rcpp::export]]
arma::vec savgol_rcpp(const arma::vec& y, int window_size, int poly_order) {
  if(window_size % 2 == 0) {
    Rcpp::stop("window_size must be odd");
  }
  
  if(window_size < poly_order + 1) {
    Rcpp::stop("window_size is too small for the polynomials order");
  }
  
  return sgolayfilt(y, window_size, poly_order);
}
