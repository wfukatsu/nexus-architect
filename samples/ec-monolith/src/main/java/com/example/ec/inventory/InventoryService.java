package com.example.ec.inventory;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class InventoryService {

    private final InventoryRepository inventoryRepository;

    public InventoryService(InventoryRepository inventoryRepository) {
        this.inventoryRepository = inventoryRepository;
    }

    public Inventory getByProductId(Long productId) {
        return inventoryRepository.findByProductId(productId)
            .orElseThrow(() -> new RuntimeException("Inventory not found for product: " + productId));
    }

    @Transactional
    public void reserve(Long productId, int quantity) {
        Inventory inv = getByProductId(productId);
        if (inv.getAvailable() < quantity) {
            throw new RuntimeException("Insufficient stock for product: " + productId +
                ", available=" + inv.getAvailable() + ", requested=" + quantity);
        }
        // [DEBT] 楽観的ロックがないため、同時注文で在庫が負になる可能性がある
        inv.setReserved(inv.getReserved() + quantity);
        inventoryRepository.save(inv);
    }

    @Transactional
    public void confirm(Long productId, int quantity) {
        Inventory inv = getByProductId(productId);
        inv.setQuantity(inv.getQuantity() - quantity);
        inv.setReserved(inv.getReserved() - quantity);
        inventoryRepository.save(inv);
    }

    @Transactional
    public void release(Long productId, int quantity) {
        Inventory inv = getByProductId(productId);
        inv.setReserved(Math.max(0, inv.getReserved() - quantity));
        inventoryRepository.save(inv);
    }

    @Transactional
    public Inventory setStock(Long productId, int quantity) {
        Inventory inv = inventoryRepository.findByProductId(productId)
            .orElseGet(() -> {
                Inventory newInv = new Inventory();
                newInv.setProductId(productId);
                newInv.setReserved(0);
                return newInv;
            });
        inv.setQuantity(quantity);
        return inventoryRepository.save(inv);
    }
}
