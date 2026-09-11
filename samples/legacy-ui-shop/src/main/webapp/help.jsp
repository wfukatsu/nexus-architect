<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<c:set var="pageTitle" value="よくあるご質問" />
<%@ include file="/WEB-INF/jspf/header.jspf" %>
<h1>よくあるご質問</h1>
<dl class="faq">
  <dt>Q. 注文後にキャンセルできますか？</dt>
  <dd>A. 出荷前であればキャンセル可能です。お問い合わせ窓口までご連絡ください。</dd>
  <dt>Q. 会員割引の条件を教えてください。</dt>
  <dd>A. 会員の方は、商品小計（税抜）が10,000円以上のご注文で10%割引となります。</dd>
  <dt>Q. 支払い方法は何が選べますか？</dt>
  <dd>A. クレジットカード、銀行振込、代金引換からお選びいただけます。</dd>
  <dt>Q. 在庫切れの商品はいつ入荷しますか？</dt>
  <dd>A. 入荷時期は商品により異なります。商品詳細画面の在庫表示をご確認ください。</dd>
</dl>
<p><a href="${ctx}/menu">メニューへ戻る</a></p>
<%@ include file="/WEB-INF/jspf/footer.jspf" %>
