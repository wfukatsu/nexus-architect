# Brief: community library reservations

A city library network (12 branches, 300,000 members) wants a reservation service.

- A member reserves a title; the first copy returned at any branch is held for them for 7 days at
  the branch they chose; they are notified; an unclaimed hold goes to the next member in the queue.
- A member may hold at most 10 active reservations; a title with more than 50 waiting members
  triggers a purchase suggestion to the acquisitions team.
- Branch staff see today's holds to shelve and the ones expiring; they can cancel a hold with a
  reason (damaged copy, member request).
- Catalogue and member records live in the existing ILS (an Oracle database, read-only for us);
  notifications go through the existing e-mail and SMS gateway; the ILS marks a copy "on hold"
  through its REST API, which is idempotent per copy id.
- Peak: the Saturday morning release of new titles — 2,000 reservations in ten minutes.
- Availability 99.9 % during opening hours; a hold must never be given to two members; a member
  must never lose their place in the queue because of a retry.
- Budget: a two-person team for six months; the city runs Kubernetes on AWS.
