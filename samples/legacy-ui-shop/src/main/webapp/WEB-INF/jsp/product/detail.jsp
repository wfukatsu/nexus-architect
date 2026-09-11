<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ taglib prefix="t" tagdir="/WEB-INF/tags" %>
<c:set var="pageTitle" value="商品詳細" />
<%@ include file="/WEB-INF/jspf/header.jspf" %>
<p class="breadcrumb"><a href="${ctx}/menu">メニュー</a> &gt; <a href="${ctx}/products">商品検索</a> &gt; 商品詳細</p>
<h1>商品詳細</h1>
<div class="product-detail">
  <img src="${ctx}/images/products/${product.image}" alt="<c:out value='${product.name}' />" width="160" height="160">
  <table class="detail-table">
    <tr><th>商品コード</th><td>${product.id}</td></tr>
    <tr><th>商品名</th><td><c:out value="${product.name}" /></td></tr>
    <tr><th>カテゴリ</th><td>${product.category}</td></tr>
    <tr><th>価格</th><td><fmt:formatNumber value="${product.price}" />円（税抜）</td></tr>
    <tr><th>在庫</th><td>${product.stock > 0 ? '在庫あり' : '在庫切れ'}</td></tr>
  </table>
</div>
<c:choose>
  <c:when test="${product.stock > 0}">
<form method="post" action="${ctx}/cart" class="add-to-cart">
  <input type="hidden" name="action" value="add">
  <input type="hidden" name="productId" value="${product.id}">
  <label for="quantity">数量</label>
  <input type="number" id="quantity" name="quantity" value="1" min="1" max="99">
  <t:button variant="primary">カートに入れる</t:button>
</form>
  </c:when>
  <c:otherwise>
<p class="error-message">この商品は現在在庫切れのため、ご注文いただけません。</p>
  </c:otherwise>
</c:choose>
<%@ include file="/WEB-INF/jspf/footer.jspf" %>
