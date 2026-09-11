package com.example.shop.web;

import java.io.IOException;

import com.example.shop.model.Cart;
import com.example.shop.model.Product;
import com.example.shop.repo.ShopData;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

@WebServlet("/cart")
public class CartServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        cartOf(req.getSession());
        req.getRequestDispatcher("/WEB-INF/jsp/cart.jsp").forward(req, res);
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        Cart cart = cartOf(req.getSession());
        String action = req.getParameter("action");
        String productId = req.getParameter("productId");

        if ("add".equals(action)) {
            Product product = ShopData.get().findProduct(productId);
            if (product != null && product.getStock() > 0) {
                cart.add(product, parseQuantity(req.getParameter("quantity")));
            }
        } else if ("remove".equals(action)) {
            cart.remove(productId);
        }
        res.sendRedirect(req.getContextPath() + "/cart");
    }

    static Cart cartOf(HttpSession session) {
        Cart cart = (Cart) session.getAttribute("cart");
        if (cart == null) {
            cart = new Cart();
            session.setAttribute("cart", cart);
        }
        return cart;
    }

    private static int parseQuantity(String value) {
        try {
            int quantity = Integer.parseInt(value);
            return Math.min(Math.max(quantity, 1), 99);
        } catch (NumberFormatException e) {
            return 1;
        }
    }
}
