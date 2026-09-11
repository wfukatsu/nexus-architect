/*
 * validation.js - input checks for the order entry form (requires jQuery).
 */
$(function () {
  var POSTAL_CODE_PATTERN = /^\d{3}-\d{4}$/;

  function showError($field, message) {
    $field.after('<span class="field-error">' + message + '</span>');
  }

  $('#orderEntryForm').on('submit', function (event) {
    var valid = true;
    $(this).find('.field-error').remove();

    var $postalCode = $('#postalCode');
    if (!POSTAL_CODE_PATTERN.test($.trim($postalCode.val()))) {
      showError($postalCode, '郵便番号は「123-4567」の形式で入力してください。');
      valid = false;
    }

    if (!valid) {
      event.preventDefault();
    }
  });
});
