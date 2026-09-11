package com.example.shop.web;

import java.io.IOException;

import com.example.shop.model.Cart;
import com.example.shop.model.Order;
import com.example.shop.model.OrderForm;
import com.example.shop.model.User;
import com.example.shop.repo.ShopData;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

@WebServlet("/order/confirm")
public class OrderConfirmServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        HttpSession session = req.getSession();
        if (session.getAttribute("orderForm") == null || CartServlet.cartOf(session).isEmpty()) {
            res.sendRedirect(req.getContextPath() + "/order/entry");
            return;
        }
        req.getRequestDispatcher("/WEB-INF/jsp/order/confirm.jsp").forward(req, res);
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse res) throws IOException {
        HttpSession session = req.getSession();
        Cart cart = CartServlet.cartOf(session);
        OrderForm form = (OrderForm) session.getAttribute("orderForm");
        Integer discount = (Integer) session.getAttribute("discount");
        Integer tax = (Integer) session.getAttribute("orderTax");
        Integer total = (Integer) session.getAttribute("orderTotal");
        if (form == null || cart.isEmpty() || discount == null || tax == null || total == null) {
            res.sendRedirect(req.getContextPath() + "/order/entry");
            return;
        }

        User user = (User) session.getAttribute("loginUser");
        Order order = ShopData.get().placeOrder(user.getId(), cart.getLines(), form,
                cart.getSubtotal(), discount, tax, total);

        session.removeAttribute("cart");
        session.removeAttribute("orderForm");
        session.removeAttribute("discount");
        session.removeAttribute("orderTax");
        session.removeAttribute("orderTotal");
        session.setAttribute("lastOrderNo", order.getOrderNo());
        res.sendRedirect(req.getContextPath() + "/order/complete");
    }
}
