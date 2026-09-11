<%@ tag pageEncoding="UTF-8" body-content="scriptless" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ attribute name="variant" required="true" description="primary | secondary" %>
<%@ attribute name="type" required="false" description="button type, default submit" %>
<%@ attribute name="name" required="false" %>
<%@ attribute name="value" required="false" %>
<%-- Standard action button. Use variant="primary" for the main action of a screen. --%>
<button type="${empty type ? 'submit' : type}" class="btn btn-${variant}"<c:if test="${not empty name}"> name="${name}" value="${value}"</c:if>><jsp:doBody /></button>
