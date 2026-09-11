/*
 * cart.js - shopping cart screen (requires jQuery).
 * Fills in the amount column of each cart line.
 */
$(function () {
  function formatYen(amount) {
    return String(amount).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '円';
  }

  $('tr.cart-line').each(function () {
    var price = parseInt($(this).data('price'), 10);
    var quantity = parseInt($(this).data('quantity'), 10);
    var lineTotal = price * quantity;
    $(this).find('.line-total').text(formatYen(lineTotal));
  });
});
