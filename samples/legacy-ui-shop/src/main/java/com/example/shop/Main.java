package com.example.shop;

import java.io.File;

import org.apache.catalina.Context;
import org.apache.catalina.WebResourceRoot;
import org.apache.catalina.startup.Tomcat;
import org.apache.catalina.webresources.DirResourceSet;
import org.apache.catalina.webresources.StandardRoot;

/**
 * Starts an embedded Tomcat serving {@code src/main/webapp} as the web application root.
 *
 * <p>The compiled classes directory is mounted at {@code /WEB-INF/classes} so that the
 * {@code @WebServlet} / {@code @WebFilter} annotations are discovered exactly as they would be
 * in a WAR deployment.
 */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        File webappDir = new File(System.getProperty("shop.webappDir", "src/main/webapp")).getAbsoluteFile();
        File baseDir = new File(System.getProperty("shop.baseDir", "build/tomcat")).getAbsoluteFile();
        File classesDir = new File(Main.class.getProtectionDomain().getCodeSource().getLocation().toURI());

        Tomcat tomcat = new Tomcat();
        tomcat.setBaseDir(baseDir.getPath());
        tomcat.setPort(port);
        tomcat.getConnector();

        Context context = tomcat.addWebapp("", webappDir.getPath());
        WebResourceRoot resources = new StandardRoot(context);
        resources.addPreResources(
                new DirResourceSet(resources, "/WEB-INF/classes", classesDir.getPath(), "/"));
        context.setResources(resources);

        tomcat.start();
        System.out.println("legacy-ui-shop started: http://localhost:" + port + "/login");
        tomcat.getServer().await();
    }
}
