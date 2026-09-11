<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ page import="com.example.shop.model.Cart" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ taglib prefix="t" tagdir="/WEB-INF/tags" %>
<c:set var="pageTitle" value="ご注文内容の確認" />
<%@ include file="/WEB-INF/jspf/header.jspf" %>
<%
    Cart cart = (Cart) session.getAttribute("cart");
    Integer discountValue = (Integer) session.getAttribute("discount");
    int subtotal = cart.getSubtotal();
    int discount = discountValue != null ? discountValue.intValue() : 0;
    // Consumption tax 10% (8% before Oct 2019), fractions rounded down.
    int tax = (int) Math.floor((subtotal - discount) * 0.10);
    int total = subtotal - discount + tax;
    session.setAttribute("orderTax", Integer.valueOf(tax));
    session.setAttribute("orderTotal", Integer.valueOf(total));
    pageContext.setAttribute("subtotal", subtotal);
    pageContext.setAttribute("discount", discount);
    pageContext.setAttribute("tax", tax);
    pageContext.setAttribute("total", total);
%>
<p class="breadcrumb"><a href="${ctx}/menu">メニュー</a> &gt; <a href="${ctx}/cart">ショッピングカート</a> &gt; ご注文内容の確認</p>
<h1>ご注文内容の確認</h1>
<ol class="steps">
  <li>1. 情報入力</li>
  <li class="active">2. 内容確認</li>
  <li>3. 完了</li>
</ol>
<h2>ご注文商品</h2>
<table class="list-table">
  <thead>
    <tr><th>商品名</th><th>単価</th><th>数量</th><th>金額</th></tr>
  </thead>
  <tbody>
    <c:forEach var="line" items="${sessionScope.cart.lines}">
    <tr>
      <td><c:out value="${line.product.name}" /></td>
      <td class="num"><fmt:formatNumber value="${line.product.price}" />円</td>
      <td class="num">${line.quantity}</td>
      <td class="num"><fmt:formatNumber value="${line.lineTotal}" />円</td>
    </tr>
    </c:forEach>
  </tbody>
</table>
<table class="amount-table">
  <tr><th>商品小計（税抜）</th><td class="num"><fmt:formatNumber value="${subtotal}" />円</td></tr>
  <tr><th>会員割引</th><td class="num">-<fmt:formatNumber value="${discount}" />円</td></tr>
  <tr><th>消費税（10%）</th><td class="num"><fmt:formatNumber value="${tax}" />円</td></tr>
  <tr class="total"><th>お支払い合計</th><td class="num"><fmt:formatNumber value="${total}" />円</td></tr>
</table>
<h2>お届け先・お支払い方法</h2>
<table class="detail-table">
  <tr><th>お届け先氏名</th><td><c:out value="${sessionScope.orderForm.shippingName}" /></td></tr>
  <tr><th>郵便番号</th><td><c:out value="${sessionScope.orderForm.postalCode}" /></td></tr>
  <tr><th>住所</th><td><c:out value="${sessionScope.orderForm.address}" /></td></tr>
  <tr><th>電話番号</th><td><c:out value="${sessionScope.orderForm.phone}" /></td></tr>
  <tr><th>メールアドレス</th><td><c:out value="${sessionScope.orderForm.email}" /></td></tr>
  <tr><th>お支払い方法</th><td>${sessionScope.orderForm.paymentMethodLabel}</td></tr>
  <tr><th>備考</th><td><c:out value="${sessionScope.orderForm.notes}" /></td></tr>
</table>
<form method="post" action="${ctx}/order/confirm">
  <div class="form-actions">
    <a href="${ctx}/order/entry" class="link-back">入力画面に戻る</a>
    <t:button variant="primary">注文を確定する</t:button>
  </div>
</form>
<%@ include file="/WEB-INF/jspf/footer.jspf" %>
