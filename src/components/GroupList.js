import {
    Box,
    Paper,
    Skeleton,
    List,
    Typography,
    ListItem,
    Avatar,
    Stack
} from "@mui/material";
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import axios from "axios";

export default function GroupList(props) {
    const [groups, setGroups] = useState(null);
    const skeletons = [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    ];

    useEffect(() => {
        if (props.token) {
            axios({
                method: "GET",
                url: "/api/grouplist",
                headers: {
                    Authorization: "Bearer " + props.token,
                },
            })
                .then((response) => {
                    const res = response.data;
                    setGroups(res);
                })
                .catch((error) => {
                    if (error.response) {
                        console.log(error.response);
                        console.log(error.response.status);
                        console.log(error.response.headers);
                    }
                });
        }
    }, []);

    return (
        <Box>
            <List disablePadding>
                {groups ? (
                    <>
                        {groups.map((group, i) => {
                            return (
                                <ListItem disablePadding spacing={0} alignItems="flex-start">
                                    <Paper
                                        key={i}
                                        sx={{
                                            width: "100%",
                                            display: "flex",
                                        }}
                                        variant="outlined"
                                    >
                                        <Link
                                            to="/chat"
                                            state={{ groupId: group.id }}
                                            style={{
                                                display: "flex",
                                                textDecoration: "none",
                                                color: "inherit",
                                                width: "100%",
                                            }}
                                        >
                                            <Stack p={2}>
                                                <Avatar
                                                    src={group.picturePath}
                                                    alt={
                                                        group.name +
                                                        " group picture"
                                                    }
                                                />
                                                <Typography
                                                    pl={2}
                                                >
                                                    {group.name.replace(
                                                        /\b\w/,
                                                        (c) => c.toUpperCase()
                                                    )}
                                                </Typography>
                                            </Stack>
                                        </Link>
                                    </Paper>
                                </ListItem>
                            );
                        })}
                    </>
                ) : (
                    skeletons.map((e, i) => {
                        return (
                            <ListItem sx={{ padding: "1px" }} key={i}>
                                <Skeleton
                                    variant="rectangle"
                                    width={280}
                                    height={80}
                                />
                            </ListItem>
                        );
                    })
                )}
            </List>
        </Box>
    );
}