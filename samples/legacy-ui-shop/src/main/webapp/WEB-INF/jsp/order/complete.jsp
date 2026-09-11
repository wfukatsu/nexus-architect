<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>ご注文完了 | オフィス用品通販システム</title>
<link rel="stylesheet" href="${pageContext.request.contextPath}/css/common.css">
</head>
<body>
<div class="title-bar">
  <span class="app-name">オフィス用品通販システム</span>
</div>
<div class="content">
  <ol class="steps">
    <li>1. 情報入力</li>
    <li>2. 内容確認</li>
    <li class="active">3. 完了</li>
  </ol>
  <h1>ご注文完了</h1>
  <div class="complete-box">
    <p>ご注文ありがとうございました。</p>
    <p>ご注文番号：<strong><c:out value="${orderNo}" /></strong></p>
    <p>ご入力いただいたメールアドレスに注文確認メールをお送りしました。</p>
  </div>
</div>
</body>
</html>
