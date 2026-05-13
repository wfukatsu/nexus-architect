package com.example.ec.order;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {

    // [DEBT] FETCH JOIN なしで取得するため、Controller で items にアクセスすると N+1 が発生 (R7)
    List<Order> findByUserId(Long userId);

    List<Order> findByUserEmail(String email);
}
