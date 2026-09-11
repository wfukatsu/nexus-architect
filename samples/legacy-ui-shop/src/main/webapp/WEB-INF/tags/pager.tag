<%@ tag pageEncoding="UTF-8" body-content="empty" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ attribute name="current" required="true" type="java.lang.Integer" %>
<%@ attribute name="totalPages" required="true" type="java.lang.Integer" %>
<%@ attribute name="baseUrl" required="true" description="URL ending in '?' or '&amp;'; page=N is appended" %>
<%-- Simple pager: previous / page numbers / next. Hidden when there is only one page. --%>
<c:if test="${totalPages > 1}">
<div class="pager">
  <c:choose>
    <c:when test="${current > 1}"><a href="${baseUrl}page=${current - 1}">&laquo; 前へ</a></c:when>
    <c:otherwise><span class="disabled">&laquo; 前へ</span></c:otherwise>
  </c:choose>
  <c:forEach var="i" begin="1" end="${totalPages}">
    <c:choose>
      <c:when test="${i == current}"><span class="current">${i}</span></c:when>
      <c:otherwise><a href="${baseUrl}page=${i}">${i}</a></c:otherwise>
    </c:choose>
  </c:forEach>
  <c:choose>
    <c:when test="${current < totalPages}"><a href="${baseUrl}page=${current + 1}">次へ &raquo;</a></c:when>
    <c:otherwise><span class="disabled">次へ &raquo;</span></c:otherwise>
  </c:choose>
</div>
</c:if>
