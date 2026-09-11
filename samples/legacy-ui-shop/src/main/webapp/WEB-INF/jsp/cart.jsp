<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ taglib prefix="t" tagdir="/WEB-INF/tags" %>
<c:set var="pageTitle" value="ショッピングカート" />
<%@ include file="/WEB-INF/jspf/header.jspf" %>
<p class="breadcrumb"><a href="${ctx}/menu">メニュー</a> &gt; ショッピングカート</p>
<h1>ショッピングカート</h1>
<c:choose>
  <c:when test="${empty sessionScope.cart.lines}">
    <p>カートに商品が入っていません。</p>
    <p><a href="${ctx}/products">商品を探す</a></p>
  </c:when>
  <c:otherwise>
    <table class="list-table cart-table">
      <thead>
        <tr><th>商品名</th><th>単価</th><th>数量</th><th>金額</th><th></th></tr>
      </thead>
      <tbody>
        <c:forEach var="line" items="${sessionScope.cart.lines}">
        <tr class="cart-line" data-price="${line.product.price}" data-quantity="${line.quantity}">
          <td><c:out value="${line.product.name}" /></td>
          <td class="num"><fmt:formatNumber value="${line.product.price}" />円</td>
          <td class="num">${line.quantity}</td>
          <td class="num line-total"></td>
          <td>
            <form method="post" action="${ctx}/cart">
              <input type="hidden" name="action" value="remove">
              <input type="hidden" name="productId" value="${line.product.id}">
              <t:button variant="secondary">削除</t:button>
            </form>
          </td>
        </tr>
        </c:forEach>
      </tbody>
      <tfoot>
        <tr><th colspan="3">合計（税抜）</th><td class="num"><fmt:formatNumber value="${sessionScope.cart.subtotal}" />円</td><td></td></tr>
      </tfoot>
    </table>
    <p class="cart-notes">※表示価格はすべて税抜です。消費税および会員割引はご注文手続きの画面で計算されます。在庫状況によりお届けまでお時間をいただく場合があります。</p>
    <div class="form-actions">
      <a href="${ctx}/products" class="link-back">買い物を続ける</a>
      <form method="get" action="${ctx}/order/entry" class="inline">
        <t:button variant="primary">注文手続きへ進む</t:button>
      </form>
    </div>
  </c:otherwise>
</c:choose>
<script src="${ctx}/js/cart.js"></script>
<%@ include file="/WEB-INF/jspf/footer.jspf" %>
