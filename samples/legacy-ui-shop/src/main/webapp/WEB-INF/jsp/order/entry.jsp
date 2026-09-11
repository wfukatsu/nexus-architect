<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ page import="com.example.shop.model.Cart" %>
<%@ page import="com.example.shop.model.User" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ taglib prefix="fn" uri="jakarta.tags.functions" %>
<%@ taglib prefix="t" tagdir="/WEB-INF/tags" %>
<c:set var="pageTitle" value="ご注文情報の入力" />
<%@ include file="/WEB-INF/jspf/header.jspf" %>
<%
    // Member discount: 10% off when the cart subtotal reaches 10,000 yen (members only).
    Cart cart = (Cart) session.getAttribute("cart");
    User user = (User) session.getAttribute("loginUser");
    int subtotal = cart.getSubtotal();
    int discount = 0;
    if (user.isMember() && subtotal >= 10000) {
        discount = (int) Math.floor(subtotal * 0.1);
    }
    session.setAttribute("discount", Integer.valueOf(discount));
    pageContext.setAttribute("subtotal", subtotal);
    pageContext.setAttribute("discount", discount);
%>
<p class="breadcrumb"><a href="${ctx}/menu">メニュー</a> &gt; <a href="${ctx}/cart">ショッピングカート</a> &gt; ご注文情報の入力</p>
<h1>ご注文情報の入力</h1>
<ol class="steps">
  <li class="active">1. 情報入力</li>
  <li>2. 内容確認</li>
  <li>3. 完了</li>
</ol>
<div class="summary-box">
  <dl>
    <dt>商品小計（税抜）</dt>
    <dd><fmt:formatNumber value="${subtotal}" />円</dd>
    <dt>会員割引</dt>
    <dd>-<fmt:formatNumber value="${discount}" />円</dd>
  </dl>
</div>
<c:if test="${not empty errors}">
  <div class="error-box">
    <p>入力内容に誤りがあります。以下の項目をご確認ください。</p>
    <ul>
      <c:forEach var="e" items="${errors}"><li>${e.value}</li></c:forEach>
    </ul>
  </div>
</c:if>
<form id="orderEntryForm" method="post" action="${ctx}/order/entry">
  <div class="form-row">
    <label for="shippingName">お届け先氏名<span class="required">必須</span></label>
    <input type="text" id="shippingName" name="shippingName" value="${fn:escapeXml(form.shippingName)}" autocomplete="name">
  </div>
  <div class="form-row">
    <label for="postalCode">郵便番号<span class="required">必須</span></label>
    <input type="text" id="postalCode" name="postalCode" value="${fn:escapeXml(form.postalCode)}" maxlength="8" autocomplete="postal-code">
    <span class="hint">例：123-4567</span>
  </div>
  <div class="form-row">
    <label for="address">住所<span class="required">必須</span></label>
    <input type="text" id="address" name="address" value="${fn:escapeXml(form.address)}" class="wide" autocomplete="street-address">
  </div>
  <div class="form-row">
    <span class="form-label">電話番号<span class="required">必須</span></span>
    <input type="text" name="phone" value="${fn:escapeXml(form.phone)}" autocomplete="tel">
  </div>
  <div class="form-row">
    <label for="email">メールアドレス<span class="required">必須</span></label>
    <input type="text" id="email" name="email" value="${fn:escapeXml(form.email)}" class="wide" autocomplete="email">
    <span class="hint">注文確認メールの送信先を入力してください。</span>
  </div>
  <fieldset class="form-row">
    <legend>お支払い方法<span class="required">必須</span></legend>
    <label class="radio"><input type="radio" name="paymentMethod" value="CARD"${form.paymentMethod == 'CARD' ? ' checked' : ''}> クレジットカード</label>
    <label class="radio"><input type="radio" name="paymentMethod" value="BANK"${form.paymentMethod == 'BANK' ? ' checked' : ''}> 銀行振込</label>
    <label class="radio"><input type="radio" name="paymentMethod" value="COD"${form.paymentMethod == 'COD' ? ' checked' : ''}> 代金引換</label>
  </fieldset>
  <div class="form-row">
    <label for="notes">備考</label>
    <textarea id="notes" name="notes" rows="3" cols="50">${fn:escapeXml(form.notes)}</textarea>
  </div>
  <div class="form-actions">
    <a href="${ctx}/cart" class="link-back">カートに戻る</a>
    <t:button variant="primary">確認画面へ進む</t:button>
  </div>
</form>
<script src="${ctx}/js/validation.js"></script>
<%@ include file="/WEB-INF/jspf/footer.jspf" %>
