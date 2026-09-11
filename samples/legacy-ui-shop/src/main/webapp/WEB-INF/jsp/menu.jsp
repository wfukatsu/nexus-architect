<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ page import="com.example.shop.model.User" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<c:set var="pageTitle" value="メニュー" />
<%@ include file="/WEB-INF/jspf/header.jspf" %>
<h1>メニュー</h1>
<ul class="menu-list">
  <li>
    <a href="${ctx}/products">商品検索</a>
    <span class="menu-desc">キーワードやカテゴリで商品を探します。</span>
  </li>
  <li>
    <a href="${ctx}/cart">ショッピングカート</a>
    <span class="menu-desc">カートの内容を確認し、注文手続きへ進みます。</span>
  </li>
<%
    User loginUser = (User) session.getAttribute("loginUser");
    if (loginUser != null && "admin".equals(loginUser.getRole())) {
%>
  <li>
    <a href="${ctx}/admin/products/edit">商品メンテナンス</a>
    <span class="menu-desc">商品の登録、価格・在庫の変更を行います。</span>
  </li>
<%
    }
%>
</ul>
<div class="account-box">
  <h2>アカウント情報</h2>
  <dl>
    <dt>氏名</dt>
    <dd><c:out value="${sessionScope.loginUser.name}" /></dd>
    <dt>メールアドレス</dt>
    <dd><c:out value="${sessionScope.loginUser.email}" /></dd>
  </dl>
</div>
<%@ include file="/WEB-INF/jspf/footer.jspf" %>
