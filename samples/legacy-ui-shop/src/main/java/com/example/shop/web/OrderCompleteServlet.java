package com.example.shop.web;

import java.io.IOException;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@WebServlet("/order/complete")
public class OrderCompleteServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        Object orderNo = req.getSession().getAttribute("lastOrderNo");
        if (orderNo == null) {
            res.sendRedirect(req.getContextPath() + "/menu");
            return;
        }
        req.setAttribute("orderNo", orderNo);
        req.getRequestDispatcher("/WEB-INF/jsp/order/complete.jsp").forward(req, res);
    }
}
