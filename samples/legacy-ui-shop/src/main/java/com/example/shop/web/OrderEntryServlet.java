package com.example.shop.web;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

import com.example.shop.model.Cart;
import com.example.shop.model.OrderForm;
import com.example.shop.model.User;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

@WebServlet("/order/entry")
public class OrderEntryServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        HttpSession session = req.getSession();
        Cart cart = CartServlet.cartOf(session);
        if (cart.isEmpty()) {
            res.sendRedirect(req.getContextPath() + "/cart");
            return;
        }
        OrderForm form = (OrderForm) session.getAttribute("orderForm");
        if (form == null) {
            User user = (User) session.getAttribute("loginUser");
            form = new OrderForm();
            form.setShippingName(user.getName());
            form.setPaymentMethod("CARD");
        }
        req.setAttribute("form", form);
        req.getRequestDispatcher("/WEB-INF/jsp/order/entry.jsp").forward(req, res);
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        HttpSession session = req.getSession();
        if (CartServlet.cartOf(session).isEmpty()) {
            res.sendRedirect(req.getContextPath() + "/cart");
            return;
        }

        OrderForm form = new OrderForm();
        form.setShippingName(trim(req.getParameter("shippingName")));
        form.setPostalCode(trim(req.getParameter("postalCode")));
        form.setAddress(trim(req.getParameter("address")));
        form.setPhone(trim(req.getParameter("phone")));
        form.setEmail(trim(req.getParameter("email")));
        form.setPaymentMethod(trim(req.getParameter("paymentMethod")));
        form.setNotes(trim(req.getParameter("notes")));

        Map<String, String> errors = new LinkedHashMap<>();
        required(errors, "shippingName", form.getShippingName(), "お届け先氏名を入力してください。");
        required(errors, "postalCode", form.getPostalCode(), "郵便番号を入力してください。");
        required(errors, "address", form.getAddress(), "住所を入力してください。");
        required(errors, "phone", form.getPhone(), "電話番号を入力してください。");
        required(errors, "email", form.getEmail(), "メールアドレスを入力してください。");
        if (!errors.containsKey("email") && !form.getEmail().contains("@")) {
            errors.put("email", "メールアドレスの形式が正しくありません。");
        }
        if (form.getPaymentMethodLabel().isEmpty()) {
            errors.put("paymentMethod", "お支払い方法を選択してください。");
        }

        if (!errors.isEmpty()) {
            req.setAttribute("errors", errors);
            req.setAttribute("form", form);
            req.getRequestDispatcher("/WEB-INF/jsp/order/entry.jsp").forward(req, res);
            return;
        }
        session.setAttribute("orderForm", form);
        res.sendRedirect(req.getContextPath() + "/order/confirm");
    }

    private static void required(Map<String, String> errors, String field, String value, String message) {
        if (value.isEmpty()) {
            errors.put(field, message);
        }
    }

    private static String trim(String value) {
        return value == null ? "" : value.trim();
    }
}
