# Recurring order-value review

NovaMart's finance operations manager asks for completed order value every month. The result is used to reconcile the commerce report before it is shared with leadership.

The practice database contains `orders` and `order_items`. `orders.total_amount` stores the order-level amount. An order may contain several item rows. Only orders whose status is exactly `completed` belong in this review.

The evaluation case should determine whether the AI analyst can answer this recurring request without duplicating order-level value, using the wrong population, or presenting an unsupported amount. The reviewer needs to be able to reproduce the expected result independently.

Design the case before opening the existing Week 3 course case or its reviewed reference. Decide the intended user, decision, observable criteria, forbidden behavior, independent reference method, tolerance, grader for each criterion, human-review boundary, slices, lifecycle status, and consequence if wrong.

Do not calculate or include the expected amount in the public proposed case.
