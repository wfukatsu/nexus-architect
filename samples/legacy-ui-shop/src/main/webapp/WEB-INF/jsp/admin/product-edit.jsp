<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ page import="com.example.shop.model.User" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fn" uri="jakarta.tags.functions" %>
<%@ taglib prefix="t" tagdir="/WEB-INF/tags" %>
<c:set var="pageTitle" value="商品編集" />
<c:set var="extraCss" value="admin.css" />
<%@ include file="/WEB-INF/jspf/header.jspf" %>
<%
    User user = (User) session.getAttribute("loginUser");
    if (user == null || !"admin".equals(user.getRole())) {
%>
<p class="error-message">この画面を表示する権限がありません。</p>
<p><a href="${ctx}/menu">メニューへ戻る</a></p>
<%
    } else {
%>
<p class="breadcrumb"><a href="${ctx}/menu">メニュー</a> &gt; 商品編集</p>
<div class="admin-panel">
  <h1>商品編集</h1>
  <c:if test="${param.saved == '1'}">
    <p class="info-message">保存しました。</p>
  </c:if>
  <c:if test="${not empty errors}">
    <p class="error-message">エラーが発生しました</p>
  </c:if>
  <form method="post" action="${ctx}/admin/products/edit">
    <input type="hidden" name="id" value="${product.id}">
    <div class="form-row">
      <span class="form-label">商品コード</span>
      <span>${empty product.id ? '（新規登録）' : product.id}</span>
    </div>
    <div class="form-row">
      <label for="name">商品名</label>
      <input type="text" id="name" name="name" value="${fn:escapeXml(product.name)}" class="wide">
    </div>
    <div class="form-row">
      <label for="price">価格（税抜）</label>
      <input type="text" id="price" name="price" value="${product.price}"> 円
    </div>
    <div class="form-row">
      <label for="stock">在庫数</label>
      <input type="text" id="stock" name="stock" value="${product.stock}">
    </div>
    <div class="form-row">
      <label for="category">カテゴリ</label>
      <select id="category" name="category">
        <c:forEach var="cat" items="${categories}">
          <option value="${cat}"${cat == product.category ? ' selected' : ''}>${cat}</option>
        </c:forEach>
      </select>
    </div>
    <div class="admin-actions">
      <button type="submit" name="action" value="save" style="background-color: #1a73e8; color: #fff; padding: 4px 20px; border: none; border-radius: 12px; font-size: 13px;">保存</button>
      <c:if test="${not empty product.id}">
        <t:button variant="secondary" name="action" value="delete">削除</t:button>
      </c:if>
      <a href="${ctx}/products">商品一覧へ</a>
    </div>
  </form>
</div>
<%
    }
%>
<%@ include file="/WEB-INF/jspf/footer.jspf" %>
