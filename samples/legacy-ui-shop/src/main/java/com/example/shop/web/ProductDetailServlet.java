package com.example.shop.web;

import java.io.IOException;

import com.example.shop.model.Product;
import com.example.shop.repo.ShopData;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@WebServlet("/products/detail")
public class ProductDetailServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        Product product = ShopData.get().findProduct(req.getParameter("id"));
        if (product == null) {
            res.sendError(HttpServletResponse.SC_NOT_FOUND, "指定された商品は見つかりません。");
            return;
        }
        req.setAttribute("product", product);
        req.getRequestDispatcher("/WEB-INF/jsp/product/detail.jsp").forward(req, res);
    }
}
