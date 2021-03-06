import graphene


class CountConnection(graphene.Connection):
    class Meta:
        abstract = True

    count = graphene.Int(
        description="Count of nodes on this connection with filters applied",
        required=True,
    )
    total_count = graphene.Int(
        description="Total count of nodes on this connection regardless of filters",
        required=True,
    )

    def resolve_count(self, info):
        return self.length

    def resolve_total_count(self, info, **kwargs):
        return self.iterable.model.objects.count()
