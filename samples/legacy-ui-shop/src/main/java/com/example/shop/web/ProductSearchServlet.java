package com.example.shop.web;

import java.io.IOException;
import java.util.List;

import com.example.shop.model.Product;
import com.example.shop.repo.ShopData;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@WebServlet("/products")
public class ProductSearchServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private static final int PAGE_SIZE = 5;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        String keyword = trimToEmpty(req.getParameter("keyword"));
        String category = trimToEmpty(req.getParameter("category"));

        List<Product> hits = ShopData.get().searchProducts(keyword, category);
        int totalPages = Math.max(1, (hits.size() + PAGE_SIZE - 1) / PAGE_SIZE);
        int currentPage = parsePage(req.getParameter("page"), totalPages);
        int from = (currentPage - 1) * PAGE_SIZE;
        int to = Math.min(from + PAGE_SIZE, hits.size());

        req.setAttribute("keyword", keyword);
        req.setAttribute("category", category);
        req.setAttribute("categories", ShopData.get().categories());
        req.setAttribute("hitCount", hits.size());
        req.setAttribute("products", hits.subList(from, to));
        req.setAttribute("currentPage", currentPage);
        req.setAttribute("totalPages", totalPages);
        req.getRequestDispatcher("/WEB-INF/jsp/product/search.jsp").forward(req, res);
    }

    private static String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private static int parsePage(String value, int totalPages) {
        try {
            int page = Integer.parseInt(value);
            return Math.min(Math.max(page, 1), totalPages);
        } catch (NumberFormatException e) {
            return 1;
        }
    }
}
