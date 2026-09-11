<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ taglib prefix="fn" uri="jakarta.tags.functions" %>
<%@ taglib prefix="t" tagdir="/WEB-INF/tags" %>
<fmt:message key="search.title" var="pageTitle" />
<%@ include file="/WEB-INF/jspf/header.jspf" %>
<p class="breadcrumb"><a href="${ctx}/menu"><fmt:message key="search.backToMenu" /></a></p>
<h1><fmt:message key="search.title" /></h1>
<form class="search-form" method="get" action="${ctx}/products">
  <input type="text" name="keyword" value="${fn:escapeXml(keyword)}" placeholder="<fmt:message key='search.keyword.placeholder' />">
  <label for="category"><fmt:message key="search.category" /></label>
  <select id="category" name="category">
    <option value=""><fmt:message key="search.category.all" /></option>
    <c:forEach var="cat" items="${categories}">
      <option value="${cat}"${cat == category ? ' selected' : ''}>${cat}</option>
    </c:forEach>
  </select>
  <t:button variant="primary"><fmt:message key="search.submit" /></t:button>
</form>
<p class="hit-count"><fmt:message key="search.hitCount"><fmt:param value="${hitCount}" /></fmt:message></p>
<c:choose>
  <c:when test="${empty products}">
    <p><fmt:message key="search.noResult" /></p>
  </c:when>
  <c:otherwise>
    <table class="list-table">
      <thead>
        <tr>
          <th><fmt:message key="search.col.image" /></th>
          <th><fmt:message key="search.col.name" /></th>
          <th><fmt:message key="search.col.price" /></th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <c:forEach var="p" items="${products}">
        <tr>
          <td class="thumb"><img src="${ctx}/images/products/${p.image}" width="64" height="64"></td>
          <td><a href="${ctx}/products/detail?id=${p.id}"><c:out value="${p.name}" /></a></td>
          <td class="num"><fmt:formatNumber value="${p.price}" />円</td>
          <td>
            <c:if test="${p.stock > 0}">
            <form method="post" action="${ctx}/cart">
              <input type="hidden" name="action" value="add">
              <input type="hidden" name="productId" value="${p.id}">
              <input type="hidden" name="quantity" value="1">
              <t:button variant="secondary"><fmt:message key="search.addToCart" /></t:button>
            </form>
            </c:if>
            <c:if test="${p.stock <= 0}"><fmt:message key="search.outOfStock" /></c:if>
          </td>
        </tr>
        </c:forEach>
      </tbody>
    </table>
    <c:url var="pagerBase" value="/products">
      <c:param name="keyword" value="${keyword}" />
      <c:param name="category" value="${category}" />
    </c:url>
    <t:pager current="${currentPage}" totalPages="${totalPages}" baseUrl="${pagerBase}&amp;" />
  </c:otherwise>
</c:choose>
<%@ include file="/WEB-INF/jspf/footer.jspf" %>
