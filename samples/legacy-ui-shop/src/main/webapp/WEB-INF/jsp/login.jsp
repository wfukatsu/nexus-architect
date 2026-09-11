<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="t" tagdir="/WEB-INF/tags" %>
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ログイン | オフィス用品通販システム</title>
<link rel="stylesheet" href="${pageContext.request.contextPath}/css/common.css">
</head>
<body class="login-page">
<div class="login-box">
  <h1>ログイン</h1>
  <c:if test="${not empty errorMessage}">
    <p class="error-message">${errorMessage}</p>
  </c:if>
  <form method="post" action="${pageContext.request.contextPath}/login">
    <div class="form-row">
      <label for="userId">ユーザーID</label>
      <input type="text" id="userId" name="userId" value="<c:out value='${param.userId}' />" autocomplete="username">
    </div>
    <div class="form-row">
      <label for="password">パスワード</label>
      <input type="password" id="password" name="password" autocomplete="current-password">
    </div>
    <div class="form-actions">
      <t:button variant="primary">ログイン</t:button>
    </div>
  </form>
</div>
</body>
</html>
