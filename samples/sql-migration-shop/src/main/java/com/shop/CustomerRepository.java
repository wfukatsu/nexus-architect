package com.shop;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/** Spring Data JPA access: one native query and one JPQL query. */
public interface CustomerRepository extends JpaRepository<Customer, Long> {

  @Query(value = "SELECT customer_id, name, region FROM customers WHERE region = :region", nativeQuery = true)
  List<Customer> byRegion(@Param("region") String region);

  @Query("SELECT c FROM Customer c WHERE c.vip = true")
  List<Customer> vipCustomers();
}
