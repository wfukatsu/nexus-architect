package com.example.shop.web;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import com.example.shop.model.Product;
import com.example.shop.repo.ShopData;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/** Product maintenance: register a new product (no id) or edit / delete an existing one. */
@WebServlet("/admin/products/edit")
public class AdminProductEditServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        String id = req.getParameter("id");
        Product product;
        if (id == null || id.isBlank()) {
            product = new Product();
            product.setCategory(ShopData.get().categories().get(0));
        } else {
            product = ShopData.get().findProduct(id);
            if (product == null) {
                res.sendError(HttpServletResponse.SC_NOT_FOUND);
                return;
            }
        }
        show(req, res, product, null);
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        String action = req.getParameter("action");
        String id = req.getParameter("id");

        if ("delete".equals(action)) {
            ShopData.get().deleteProduct(id);
            res.sendRedirect(req.getContextPath() + "/products");
            return;
        }

        Product product = new Product();
        product.setId(id == null || id.isBlank() ? null : id);
        product.setName(req.getParameter("name") == null ? "" : req.getParameter("name").trim());
        product.setCategory(req.getParameter("category"));

        List<String> errors = new ArrayList<>();
        if (product.getName().isEmpty()) {
            errors.add("name");
        }
        try {
            product.setPrice(Integer.parseInt(req.getParameter("price").trim()));
            if (product.getPrice() < 0) {
                errors.add("price");
            }
        } catch (RuntimeException e) {
            errors.add("price");
        }
        try {
            product.setStock(Integer.parseInt(req.getParameter("stock").trim()));
            if (product.getStock() < 0) {
                errors.add("stock");
            }
        } catch (RuntimeException e) {
            errors.add("stock");
        }
        if (!ShopData.get().categories().contains(product.getCategory())) {
            errors.add("category");
        }

        if (!errors.isEmpty()) {
            show(req, res, product, errors);
            return;
        }
        ShopData.get().saveProduct(product);
        res.sendRedirect(req.getContextPath() + "/admin/products/edit?id=" + product.getId() + "&saved=1");
    }

    private void show(HttpServletRequest req, HttpServletResponse res, Product product, List<String> errors)
            throws ServletException, IOException {
        req.setAttribute("product", product);
        req.setAttribute("categories", ShopData.get().categories());
        req.setAttribute("errors", errors);
        req.getRequestDispatcher("/WEB-INF/jsp/admin/product-edit.jsp").forward(req, res);
    }
}
