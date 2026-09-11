package com.example.shop.web;

import java.io.IOException;

import com.example.shop.model.User;
import com.example.shop.repo.ShopData;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

@WebServlet("/login")
public class LoginServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        req.getRequestDispatcher("/WEB-INF/jsp/login.jsp").forward(req, res);
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse res)
            throws ServletException, IOException {
        String userId = req.getParameter("userId");
        String password = req.getParameter("password");

        if (userId == null || userId.isBlank() || password == null || password.isEmpty()) {
            req.setAttribute("errorMessage", "ユーザーIDとパスワードを入力してください。");
            doGet(req, res);
            return;
        }
        User user = ShopData.get().authenticate(userId.trim(), password);
        if (user == null) {
            req.setAttribute("errorMessage", "ユーザーIDまたはパスワードが正しくありません。");
            doGet(req, res);
            return;
        }

        HttpSession old = req.getSession(false);
        if (old != null) {
            old.invalidate();
        }
        req.getSession(true).setAttribute("loginUser", user);
        res.sendRedirect(req.getContextPath() + "/menu");
    }
}
